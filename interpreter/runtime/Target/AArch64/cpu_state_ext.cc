#include "cpu_state.hh"

#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace prot::state {

namespace {
// Linux AArch64 syscall numbers
constexpr uint64_t kWrite = 64;
constexpr uint64_t kExit = 93;
constexpr uint64_t kExitGroup = 94;
} // namespace

// SVC #imm with the Linux convention: x8 = number, x0.. = arguments,
// x0 = result.
void CPU::supervisor_call(memory::Memory &mem, uint16_t /*imm*/) {
  const auto num = getX<uint64_t>(8);
  switch (num) {
  case kExit:
  case kExitGroup:
    doExit(static_cast<isa::Word>(getX<uint64_t>(0)));
    break;
  case kWrite: {
    const auto fd = getX<uint64_t>(0);
    const auto buf = getX<uint64_t>(1);
    const auto len = getX<uint64_t>(2);
    std::vector<std::byte> data(len);
    mem.readBlock(buf, data);
    std::fwrite(data.data(), 1, len, fd == 2 ? stderr : stdout);
    setX(0, len);
    break;
  }
  default:
    throw std::runtime_error{fmt::format("Unknown syscall w/ num {}", num)};
  }
}

// MOPS (CPY*, SET*): the whole operation happens in the prologue. A copy that
// may overlap behaves like memmove; a forward-only copy (CPYF*) copies bytes
// in increasing address order.
void CPU::mem_copy(memory::Memory &mem, uint64_t dst, uint64_t src, uint64_t n,
                   bool may_overlap) {
  if (may_overlap && dst > src && dst - src < n) {
    for (uint64_t i = n; i-- > 0;)
      mem.write<uint8_t>(dst + i, mem.read<uint8_t>(src + i));
    return;
  }
  for (uint64_t i = 0; i < n; ++i)
    mem.write<uint8_t>(dst + i, mem.read<uint8_t>(src + i));
}

void CPU::mem_set(memory::Memory &mem, uint64_t dst, uint64_t n, uint8_t byte) {
  for (uint64_t i = 0; i < n; ++i)
    mem.write<uint8_t>(dst + i, byte);
}

// Alignment rules of ordered, atomic and exclusive accesses: exclusives must
// be naturally aligned, the others must not cross a 16-byte boundary
// (FEAT_LSE2). A violation is an Alignment fault, which ends the program.
void CPU::check_alignment(uint64_t addr, uint8_t size, bool exclusive) {
  const bool ok = exclusive ? addr % size == 0 : addr % 16 + size <= 16;
  if (!ok) {
    throw std::runtime_error{
        fmt::format("Alignment fault: {}-byte access at {:#x}", size, addr)};
  }
}

void CPU::exclusive_mark(uint64_t addr, uint8_t size) {
  m_exclValid = true;
  m_exclAddr = addr;
  m_exclSize = size;
}

// Store-exclusive: passes if the monitor holds the same address and size;
// the monitor is cleared either way.
bool CPU::exclusive_check(uint64_t addr, uint8_t size) {
  const bool pass = m_exclValid && m_exclAddr == addr && m_exclSize == size;
  m_exclValid = false;
  return pass;
}

void CPU::exclusive_clear() { m_exclValid = false; }

// Pointer authentication of a Linux EL0 process: 48-bit virtual addresses,
// all keys enabled, top byte ignored for data pointers but not for
// instruction pointers. The PAC is an implementation-defined keyed hash of
// the pointer and the modifier; a failed authentication is a fault
// (FEAT_FPAC), which ends the program.
namespace {
// Keys IA, IB, DA, DB, GA (fixed: the simulator runs a single process)
constexpr uint64_t kPacKeys[5][2] = {
    {0x243f6a8885a308d3ULL, 0x13198a2e03707344ULL},
    {0xa4093822299f31d0ULL, 0x082efa98ec4e6c89ULL},
    {0x452821e638d01377ULL, 0xbe5466cf34e90c6cULL},
    {0xc0ac29b7c97c50ddULL, 0x3f84d5b5b5470917ULL},
    {0x9216d5d98979fb1bULL, 0xd1310ba698dfb5acULL},
};
constexpr unsigned kKeyGA = 4;
constexpr const char *kKeyNames[] = {"IA", "IB", "DA", "DB"};

uint64_t mix(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 33;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 33;
  return x;
}

uint64_t pac_hash(uint64_t ptr, uint64_t modifier, unsigned key) {
  const auto &k = kPacKeys[key];
  return mix(mix(ptr ^ k[0]) ^ modifier ^ k[1]) ^ mix(modifier + k[0]);
}

bool is_data(uint8_t key) { return key >= 2; }

// Bits of the PAC field: 54:48, and 63:56 for instruction pointers
uint64_t pac_field(bool data) {
  return data ? 0x007f000000000000ULL : 0xff7f000000000000ULL;
}

// The pointer with its PAC field replaced by copies of bit 55
uint64_t canonical(uint64_t ptr, bool data) {
  const uint64_t field = pac_field(data);
  return (ptr >> 55) & 1 ? ptr | field : ptr & ~field;
}

uint64_t add_pac(uint64_t ptr, uint64_t modifier, uint8_t key) {
  const bool data = is_data(key);
  const uint64_t field = pac_field(data);
  const uint64_t original = canonical(ptr, data);
  uint64_t pac = pac_hash(original, modifier, key) & field;
  if (ptr != original) // not a canonical pointer: corrupt the PAC
    pac ^= uint64_t{1} << 54;
  return (original & ~field) | pac;
}
} // namespace

uint64_t CPU::pac_add(uint64_t ptr, uint64_t modifier, uint8_t key) {
  return add_pac(ptr, modifier, key);
}

uint64_t CPU::pac_auth(uint64_t ptr, uint64_t modifier, uint8_t key) {
  const uint64_t original = canonical(ptr, is_data(key));
  if (add_pac(original, modifier, key) != ptr) {
    throw std::runtime_error{fmt::format(
        "Pointer authentication failure: {:#x} (key {}, modifier {:#x})", ptr,
        kKeyNames[key & 3], modifier)};
  }
  return original;
}

uint64_t CPU::pac_strip(uint64_t ptr, bool data) { return canonical(ptr, data); }

// PACGA: the upper 32 bits of the PAC of Xn with modifier Xm
uint64_t CPU::pac_generic(uint64_t value, uint64_t modifier) {
  return pac_hash(value, modifier, kKeyGA) & 0xffffffff00000000ULL;
}

// A single PE with sequentially consistent memory: barriers, hints, wait
// instructions and BTI landing pads have no effect.
void CPU::barrier(uint8_t /*type*/, uint8_t /*option*/) {}
void CPU::hint(uint8_t /*op*/) {}
void CPU::wait_timeout(bool /*wfi*/, uint64_t /*timeout*/) {}
void CPU::branch_target(uint8_t /*targets*/) {}

} // namespace prot::state

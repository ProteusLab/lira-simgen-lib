#include "cpu_state.hh"

#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
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

// Exceptions and system instructions as a Linux EL0 process sees them: the
// registers and operations Linux gives user space work, anything else is an
// Undefined Instruction (or a debug exception for BRK/HLT), which ends the
// program.
namespace {
[[noreturn]] void undefined(const std::string &what) {
  throw std::runtime_error{"Undefined instruction: " + what};
}

constexpr uint64_t sysreg(unsigned op0, unsigned op1, unsigned crn, unsigned crm,
                          unsigned op2) {
  return op0 << 14 | op1 << 11 | crn << 7 | crm << 3 | op2;
}

std::string sysreg_name(uint64_t key) {
  return fmt::format("S{}_{}_C{}_C{}_{}", key >> 14, (key >> 11) & 7, (key >> 7) & 15,
                     (key >> 3) & 15, key & 7);
}

constexpr uint64_t kTpidrEl0 = sysreg(3, 3, 13, 0, 2);
constexpr uint64_t kTpidrroEl0 = sysreg(3, 3, 13, 0, 3);
constexpr uint64_t kCtrEl0 = sysreg(3, 3, 0, 0, 1);
constexpr uint64_t kDczidEl0 = sysreg(3, 3, 0, 0, 7);
constexpr uint64_t kCntfrqEl0 = sysreg(3, 3, 14, 0, 0);
constexpr uint64_t kCntpctEl0 = sysreg(3, 3, 14, 0, 1);
constexpr uint64_t kCntvctEl0 = sysreg(3, 3, 14, 0, 2);
constexpr uint64_t kCntpctssEl0 = sysreg(3, 3, 14, 0, 5);
constexpr uint64_t kCntvctssEl0 = sysreg(3, 3, 14, 0, 6);
constexpr uint64_t kDit = sysreg(3, 3, 4, 2, 5);
constexpr uint64_t kSsbs = sysreg(3, 3, 4, 2, 6);
constexpr uint64_t kMidrEl1 = sysreg(3, 0, 0, 0, 0);
constexpr uint64_t kMpidrEl1 = sysreg(3, 0, 0, 0, 5);

// CTR_EL0: 64-byte cache lines, PIPT instruction cache; DCZID_EL0: DC ZVA
// zeroes 64 bytes; the generic timer counts executed instructions at 1 GHz
constexpr uint64_t kCtr = 0x8444c004;
constexpr uint64_t kDczid = 4;
constexpr uint64_t kZvaBytes = 4U << kDczid;
constexpr uint64_t kCntfrq = 1'000'000'000;
constexpr uint64_t kMidr = 0x410fd0c0; // implementer Arm, generic part
} // namespace

void CPU::exception_call(uint8_t kind, uint16_t imm) {
  static constexpr const char *kNames[] = {"BRK", "HLT", "HVC", "SMC", "UDF"};
  const char *name = kind < 5 ? kNames[kind] : "exception";
  if (kind == 0 || kind == 1)
    throw std::runtime_error{fmt::format("Debug exception: {} #{:#x}", name, imm)};
  undefined(fmt::format("{} #{:#x}", name, imm));
}

void CPU::exception_return(uint8_t kind) {
  static constexpr const char *kNames[] = {"ERET", "ERETAA", "ERETAB", "DRPS"};
  undefined(kNames[kind & 3]);
}

void CPU::debug_state(uint8_t level) { undefined(fmt::format("DCPS{}", level)); }

uint64_t CPU::sysreg_read(bool o0, uint8_t op1, uint8_t crn, uint8_t crm, uint8_t op2) {
  const uint64_t key = sysreg(2 + o0, op1, crn, crm, op2);
  switch (key) {
  case kTpidrEl0:
    return m_tpidrEl0;
  case kTpidrroEl0:
    return 0;
  case kCtrEl0:
    return kCtr;
  case kDczidEl0:
    return kDczid;
  case kCntfrqEl0:
    return kCntfrq;
  case kCntpctEl0:
  case kCntvctEl0:
  case kCntpctssEl0:
  case kCntvctssEl0:
    return m_icount;
  case kDit:
    return static_cast<uint64_t>(m_dit) << 24;
  case kSsbs:
    return static_cast<uint64_t>(m_ssbs) << 12;
  case kMidrEl1:
    return kMidr;
  case kMpidrEl1:
    return 0x80000000;
  default:
    // The rest of the ID register space Linux emulates reads as zero
    if (key >> 7 == sysreg(3, 0, 0, 0, 0) >> 7)
      return 0;
    undefined("MRS " + sysreg_name(key));
  }
}

void CPU::sysreg_write(bool o0, uint8_t op1, uint8_t crn, uint8_t crm, uint8_t op2,
                       uint64_t value) {
  const uint64_t key = sysreg(2 + o0, op1, crn, crm, op2);
  switch (key) {
  case kTpidrEl0:
    m_tpidrEl0 = value;
    break;
  case kDit:
    m_dit = (value >> 24) & 1;
    break;
  case kSsbs:
    m_ssbs = (value >> 12) & 1;
    break;
  default:
    undefined("MSR " + sysreg_name(key));
  }
}

void CPU::sys_op(memory::Memory &mem, uint8_t op1, uint8_t crn, uint8_t crm, uint8_t op2,
                 uint64_t value) {
  if (op1 == 3 && crn == 7 && op2 == 1) {
    switch (crm) {
    case 4: // DC ZVA
      for (uint64_t i = 0; i < kZvaBytes; ++i)
        mem.write<uint8_t>((value & ~(kZvaBytes - 1)) + i, 0);
      return;
    case 5:  // IC IVAU
    case 10: // DC CVAC
    case 11: // DC CVAU
    case 12: // DC CVAP
    case 13: // DC CVADP
    case 14: // DC CIVAC
      return;
    default:
      break;
    }
  }
  undefined(fmt::format("SYS #{}, C{}, C{}, #{}", op1, crn, crm, op2));
}

uint64_t CPU::sys_op_read(uint8_t op1, uint8_t crn, uint8_t crm, uint8_t op2) {
  undefined(fmt::format("SYSL #{}, C{}, C{}, #{}", op1, crn, crm, op2));
}

// MSR (immediate): EL0 may set DIT and SSBS
void CPU::pstate_write(uint8_t op1, uint8_t op2, uint8_t crm) {
  if (op1 == 3 && op2 == 2)
    m_dit = crm & 1;
  else if (op1 == 3 && op2 == 1)
    m_ssbs = crm & 1;
  else
    undefined(fmt::format("MSR (immediate) op1={} op2={}", op1, op2));
}

// A single PE with sequentially consistent memory: barriers, hints, wait
// instructions and BTI landing pads have no effect.
void CPU::barrier(uint8_t /*type*/, uint8_t /*option*/) {}
void CPU::hint(uint8_t /*op*/) {}
void CPU::wait_timeout(bool /*wfi*/, uint64_t /*timeout*/) {}
void CPU::branch_target(uint8_t /*targets*/) {}

} // namespace prot::state

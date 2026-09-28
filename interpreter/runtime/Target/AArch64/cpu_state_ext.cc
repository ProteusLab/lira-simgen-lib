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

// A single PE with sequentially consistent memory: barriers, hints, wait
// instructions and BTI landing pads have no effect.
void CPU::barrier(uint8_t /*type*/, uint8_t /*option*/) {}
void CPU::hint(uint8_t /*op*/) {}
void CPU::wait_timeout(bool /*wfi*/, uint64_t /*timeout*/) {}
void CPU::branch_target(uint8_t /*targets*/) {}

} // namespace prot::state

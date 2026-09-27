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

} // namespace prot::state

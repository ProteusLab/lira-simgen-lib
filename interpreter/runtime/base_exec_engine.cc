#include "base_exec_engine.hh"
#include "decoder.hh"
#include "memory.hh"

#include <fmt/core.h>
#include <stdexcept>

namespace prot::engine {
using namespace prot::state;
using namespace prot::isa;
using namespace prot::memory;

void ExecEngine::step(CPU &cpu, Memory &mem) {
  const auto bytes = mem.read<uint32_t>(cpu.getPC());
  auto instr_opt = decoder::decode(bytes);
  if (instr_opt) {
    execute(cpu, mem, *instr_opt);
    cpu.increaseICount();
  } else {
    fmt::println("DECODE FAIL pc={:#010x} inst={:#010x}", cpu.getPC(), bytes);
    throw std::runtime_error{"decode failure"};
  }
}
} // namespace prot::engine

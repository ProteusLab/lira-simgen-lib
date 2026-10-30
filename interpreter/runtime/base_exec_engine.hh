#ifndef PROT_EXEC_ENGINE_HH_INCLUDED
#define PROT_EXEC_ENGINE_HH_INCLUDED

#include "cpu_state.hh"
#include "isa.hh"
#include "memory.hh"

namespace prot::engine {
using namespace prot::state;
using namespace prot::isa;
using namespace prot::memory;

struct ExecEngine {
  virtual ~ExecEngine() = default;

  virtual void execute(CPU &cpu, Memory &mem, const Instruction &insn) = 0;
  virtual void step(CPU &cpu, Memory &mem);
};
} // namespace prot::engine

#endif // PROT_EXEC_ENGINE_HH_INCLUDED

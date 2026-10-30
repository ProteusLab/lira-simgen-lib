#ifndef PROT_HART_HH_INCLUDED
#define PROT_HART_HH_INCLUDED

#include <memory>

#include "base_exec_engine.hh"
#include "cpu_state.hh"
#include "elf_loader.hh"
#include "memory.hh"

namespace prot::hart {
using namespace prot::state;
using namespace prot::isa;
using namespace prot::elf_loader;
using namespace prot::engine;
using namespace prot::memory;

class Hart {
public:
  Hart(std::unique_ptr<Memory> mem, std::unique_ptr<ExecEngine> engine);

  void setRegister(uint32_t index, uint32_t value);

  void load(const ElfLoader &loader);

  void setPC(uint32_t addr);

  void run() {
    while (!m_cpu->m_finished) {
      m_engine->step(*m_cpu, *m_mem);
    }
  }

  auto getIcount() const { return m_cpu->m_icount; }
  auto getExitCode() const { return m_cpu->m_code; }

private:
  std::unique_ptr<Memory> m_mem;
  std::unique_ptr<CPU> m_cpu;
  std::unique_ptr<ExecEngine> m_engine;
};
} // namespace prot::hart

#endif // PROT_HART_HH_INCLUDED

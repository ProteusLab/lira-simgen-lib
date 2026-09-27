#include "hart.hh"

namespace prot::hart {
Hart::Hart(std::unique_ptr<Memory> mem, std::unique_ptr<ExecEngine> engine)
    : m_mem(std::move(mem)), m_cpu(std::make_unique<CPU>()),
      m_engine(std::move(engine)) {}

void Hart::load(const ElfLoader &loader) {
  loader.loadMemory(*m_mem);
  setPC(loader.getEntryPoint());
}

void Hart::setPC(isa::Addr addr) { m_cpu->setPC(addr); }
} // namespace prot::hart

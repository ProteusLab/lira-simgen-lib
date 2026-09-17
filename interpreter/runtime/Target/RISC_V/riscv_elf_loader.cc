#include "riscv_elf_loader.hh"

#include <elfio/elfio.hpp>

namespace prot::elf_loader {

void RiscvElfLoader::validate() const {
  ElfLoader::validate();

  if (m_elf->get_machine() != ELFIO::EM_RISCV) {
    throw std::invalid_argument{"Invalid machine"};
  }
}

RiscvElfLoader::RiscvElfLoader(std::istream &stream) : ElfLoader(stream) {
  validate();
}

RiscvElfLoader::RiscvElfLoader(const std::filesystem::path &filename)
    : ElfLoader(filename) {
  validate();
}

} // namespace prot::elf_loader

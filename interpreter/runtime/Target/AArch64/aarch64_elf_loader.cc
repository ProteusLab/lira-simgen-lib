#include "aarch64_elf_loader.hh"

#include <elfio/elfio.hpp>

namespace prot::elf_loader {

void Aarch64ElfLoader::validate() const {
  ElfLoader::validate();

  if (m_elf->get_machine() != ELFIO::EM_AARCH64) {
    throw std::invalid_argument{"Invalid machine"};
  }
}

Aarch64ElfLoader::Aarch64ElfLoader(std::istream &stream) : ElfLoader(stream) {
  validate();
}

Aarch64ElfLoader::Aarch64ElfLoader(const std::filesystem::path &filename)
    : ElfLoader(filename) {
  validate();
}

} // namespace prot::elf_loader

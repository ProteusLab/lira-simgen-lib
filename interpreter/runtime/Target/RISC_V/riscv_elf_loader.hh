#ifndef PROT_RISCV_ELF_LOADER_HH_INCLUDED
#define PROT_RISCV_ELF_LOADER_HH_INCLUDED

#include <filesystem>
#include <istream>

#include "elf_loader.hh"

namespace prot::elf_loader {

// RISC-V ELF loader: adds the machine check (EM_RISCV) on top of the
// generic validation.
class RiscvElfLoader : public ElfLoader {
public:
  explicit RiscvElfLoader(std::istream &stream);
  explicit RiscvElfLoader(const std::filesystem::path &filename);

protected:
  void validate() const override;
};

} // namespace prot::elf_loader

#endif // PROT_RISCV_ELF_LOADER_HH_INCLUDED

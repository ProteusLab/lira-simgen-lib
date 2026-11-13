#ifndef PROT_AARCH64_ELF_LOADER_HH_INCLUDED
#define PROT_AARCH64_ELF_LOADER_HH_INCLUDED

#include <filesystem>
#include <istream>

#include "elf_loader.hh"

namespace prot::elf_loader {

// AArch64 ELF loader: adds the machine check (EM_AARCH64) on top of the
// generic validation.
class Aarch64ElfLoader : public ElfLoader {
public:
  explicit Aarch64ElfLoader(std::istream &stream);
  explicit Aarch64ElfLoader(const std::filesystem::path &filename);

protected:
  void validate() const override;
};

} // namespace prot::elf_loader

#endif // PROT_AARCH64_ELF_LOADER_HH_INCLUDED

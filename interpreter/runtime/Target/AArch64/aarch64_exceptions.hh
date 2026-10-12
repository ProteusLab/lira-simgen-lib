// Exceptions of the AArch64 runtime that a caller may tell apart (the others
// are std::runtime_error)

#ifndef AARCH64_EXCEPTIONS_HH_INCLUDED
#define AARCH64_EXCEPTIONS_HH_INCLUDED

#include <cstdint>
#include <stdexcept>
#include <string>

namespace prot::state {

// An SME access trap (ESR EC 0x1D): `type` 2 for an instruction that needs
// streaming mode, 3 for one that needs ZA. A Linux process gets SIGILL.
class SmeAccessTrap : public std::runtime_error {
public:
  explicit SmeAccessTrap(uint8_t type)
      : std::runtime_error{"SME access trap (SIGILL): type " + std::to_string(type) +
                           (type == 2 ? ", not in streaming mode"
                                      : type == 3 ? ", ZA is disabled" : "")},
        m_type(type) {}

  uint8_t type() const { return m_type; }

private:
  uint8_t m_type;
};

} // namespace prot::state

#endif // AARCH64_EXCEPTIONS_HH_INCLUDED

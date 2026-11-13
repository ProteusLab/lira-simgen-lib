from interpreter.regfile import RegisterFile, ScalableRegFile


class VRegs(RegisterFile):
    """Fixed 128-bit SIMD registers, or the low 128 bits of SVE registers."""

    def read(self, index, *, cpu="cpu"):
        return f"{cpu}.getV({index})"

    def definition(self):
        if self.alias is not None:
            owner = self.alias
            return f"""// Register file: V (SIMD&FP), the low 128 bits of {owner.name}
void setV(std::size_t reg, uint128_t value) {{
  auto *bytes = reg{owner.name}(reg);
  std::memcpy(bytes, &value, sizeof(value));
  std::memset(bytes + sizeof(value), 0, {owner.max_bytes} - sizeof(value));
}}
uint128_t getV(std::size_t reg) const {{
  uint128_t value;
  std::memcpy(&value, reg{owner.name}(reg), sizeof(value));
  return value;
}}"""
        count = len(self.file.regs)
        return f"""// Register file: V (SIMD&FP)
std::array<uint128_t, {count}> m_V{{}};
void setV(std::size_t reg, uint128_t value) {{ m_V[reg] = value; }}
uint128_t getV(std::size_t reg) const {{ return m_V[reg]; }}"""


REGISTER_FILES = {"V": VRegs, **{name: ScalableRegFile for name in ("Z", "P", "FFR", "ZA")}}

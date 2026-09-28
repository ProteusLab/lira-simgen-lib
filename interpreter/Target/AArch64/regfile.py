# lira-simgen-lib/interpreter/Target/AArch64/regfile.py

from lib.regfile import RegFile, serves

from interpreter import config


@serves("X")
class XRegs(RegFile):
    """x0..x30 and sp (index 31); XZR is expressed in the LIRA semantics."""

    def read(self, index, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.getX<uint64_t>({index});"

    def write(self, index, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.setX({index}, {value});"


@serves("V")
class VRegs(RegFile):
    """v0..v31, 128 bits each; the semantics access whole registers."""

    def read(self, index, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.getV({index});"

    def write(self, index, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.setV({index}, {value});"

    @property
    def definition(self) -> str:
        n = len(self.rf.regs)
        return f"""\
  // Register file: V (SIMD&FP)
  std::array<unsigned __int128, {n}> m_V{{}};

  void setV(const std::size_t reg, const unsigned __int128 value) {{
    m_V[reg] = value;
  }}

  unsigned __int128 getV(const std::size_t reg) const {{ return m_V[reg]; }}
"""


@serves("NZCV")
class Flags(RegFile):
    """Single 4-bit register holding PSTATE.{N,Z,C,V}."""

    def read(self, index, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.m_nzcv;"

    def write(self, index, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.m_nzcv = {value};"


@serves("FPCR")
class Fpcr(RegFile):
    """Floating-point Control Register (MRS/MSR FPCR)."""

    def read(self, index, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.m_fpcr;"

    def write(self, index, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.m_fpcr = {value};"


@serves("FPSR")
class Fpsr(RegFile):
    """Floating-point Status Register (MRS/MSR FPSR)."""

    def read(self, index, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.m_fpsr;"

    def write(self, index, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.m_fpsr = {value};"

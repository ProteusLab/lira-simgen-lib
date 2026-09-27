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


@serves("NZCV")
class Flags(RegFile):
    """Single 4-bit register holding PSTATE.{N,Z,C,V}."""

    def read(self, index, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.m_nzcv;"

    def write(self, index, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.m_nzcv = {value};"

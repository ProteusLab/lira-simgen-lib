# lira-simgen-lib/interpreter/Target/RISC_V/regfile.py

from lib.operand import PC
from lib.regfile import RegFile, serves

from interpreter import config


@serves("XRegs")
class XRegs(RegFile):
    def read(self, reg, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.CPU_VAR}.getXRegs<uint32_t>({reg});"

    def write(self, reg, value) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.setXRegs({reg}, {value});"

    @property
    def set_guard(self) -> str:
        return "".join(
            f"    if (reg == {i}) return; // {reg.name} is hardwired to zero\n"
            for i, reg in enumerate(self.rf.regs)
            if "zero" in reg.attributes
        )

    @property
    def get_guard(self) -> str:
        return "".join(
            f"    if (reg == {i}) return 0; // {reg.name} is hardwired to zero\n"
            for i, reg in enumerate(self.rf.regs)
            if "zero" in reg.attributes
        )


@serves("Program Counter")
class ProgramCounter(RegFile):
    def register(self, reg) -> object:
        return PC(reg.name, self.rf.reg_size.lanes_base, rf_name=self.rf.name)

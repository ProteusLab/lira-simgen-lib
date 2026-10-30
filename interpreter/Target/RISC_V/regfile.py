# lira-simgen-lib/interpreter/Target/RISC_V/regfile.py

from lib.attributes import ZERO_ATTRIBUTE
from lib.operand import PC
from lib.regfile import serves

from interpreter import config
from interpreter.regfile import RegFile


@serves("XRegs")
class XRegs(RegFile):
    def read(self, reg, var) -> str:
        return f"{var} = {config.SimpleInterpConfig.M_CPU}.getXRegs<uint32_t>({reg});"

    def write(self, reg, value) -> str:
        return f"{config.SimpleInterpConfig.M_CPU}.setXRegs({reg}, {value});"

    @property
    def set_guard(self) -> str:
        return "".join(
            f"    if (reg == {i}) return; // {reg.name} is hardwired to zero\n"
            for i, reg in enumerate(self.rf.regs)
            if ZERO_ATTRIBUTE in reg.attributes
        )

    @property
    def get_guard(self) -> str:
        return "".join(
            f"    if (reg == {i}) return 0; // {reg.name} is hardwired to zero\n"
            for i, reg in enumerate(self.rf.regs)
            if ZERO_ATTRIBUTE in reg.attributes
        )


@serves("ProgramCounter")
class ProgramCounter(RegFile):
    def register(self, reg) -> object:
        return PC(reg.name, self.rf.reg_size.lanes_base, rf_name=self.rf.name)

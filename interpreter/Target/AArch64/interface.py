# lira-simgen-lib/interpreter/Target/AArch64/interface.py

from typing import Optional

from lib.interface import CpuInterface, serves

from interpreter import config
from interpreter.interface import ReadMem, WriteMem

CPU = config.SimpleInterpConfig.CPU_VAR
MEM = config.SimpleInterpConfig.MEM_VAR


class PcRead(CpuInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{out} = {CPU}.getPC();"

    @property
    def declaration(self) -> str:
        return ""

    @property
    def definition(self) -> str:
        return ""


class PcWrite(CpuInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{CPU}.setPC({inputs[0]});"

    @property
    def declaration(self) -> str:
        return ""

    @property
    def definition(self) -> str:
        return ""


class SupervisorCall(CpuInterface):
    """SVC #imm: served by the runtime (Linux-like syscalls)."""

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{CPU}.{self.name}({MEM}, {inputs[0]});"

    @property
    def declaration(self) -> str:
        return f"void {self.name}(prot::memory::Memory &mem, uint16_t imm);"

    @property
    def definition(self) -> str:
        return ""


serves("pc_read")(PcRead)
serves("pc_write")(PcWrite)
serves("supervisor_call")(SupervisorCall)
for _n in (8, 16, 32, 64, 128):
    serves(f"mem_read_{_n}")(ReadMem)
    serves(f"mem_write_{_n}")(WriteMem)

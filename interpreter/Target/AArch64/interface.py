# lira-simgen-lib/interpreter/Target/AArch64/interface.py

from typing import Optional

from lib.interface import CpuInterface, serves
from lib.types import OperandType

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


class RuntimeCall(CpuInterface):
    """Environment function implemented by the `CPU` method of the same name
    in the hand-written runtime (runtime/Target/AArch64/cpu_state_ext.cc)."""

    # Pass the guest memory as the first argument
    uses_mem: bool = False

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        args = ([MEM] if self.uses_mem else []) + [str(i) for i in inputs]
        call = f"{CPU}.{self.name}({', '.join(args)})"
        return f"{out} = {call};" if out else f"{call};"

    @property
    def declaration(self) -> str:
        ret = OperandType.gen(self.outputs[0]) if self.outputs else "void"
        params = (["prot::memory::Memory &mem"] if self.uses_mem else []) + [
            f"{OperandType.gen(w)} a{i}" for i, w in enumerate(self.inputs)
        ]
        return f"{ret} {self.name}({', '.join(params)});"

    @property
    def definition(self) -> str:
        return ""


class MemRuntimeCall(RuntimeCall):
    uses_mem = True


serves("pc_read")(PcRead)
serves("pc_write")(PcWrite)
for _n in (8, 16, 32, 64, 128):
    serves(f"mem_read_{_n}")(ReadMem)
    serves(f"mem_write_{_n}")(WriteMem)

# SVC #imm: Linux-like syscalls; MOPS copy and set; SYS (DC ZVA)
for _name in ("supervisor_call", "mem_copy", "mem_set", "sys_op"):
    serves(_name)(MemRuntimeCall)
# Alignment faults, the exclusive monitor, barriers and hints
for _name in (
    "check_alignment",
    "exclusive_mark",
    "exclusive_check",
    "exclusive_clear",
    "barrier",
    "hint",
    "wait_timeout",
    "branch_target",
    # Pointer authentication
    "pac_add",
    "pac_auth",
    "pac_strip",
    "pac_generic",
    # Exceptions and system registers of a Linux EL0 process
    "exception_call",
    "exception_return",
    "debug_state",
    "sys_op_read",
    "sysreg_read",
    "sysreg_write",
    "pstate_write",
):
    serves(_name)(RuntimeCall)

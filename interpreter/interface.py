# lira-simgen-lib/interpreter/interface.py

from typing import Optional

from lib.attributes import PC_ATTRIBUTE
from lib.interface import Interface

from cpp.context import Context
from cpp.types import OperandType


class CpuInterface(Interface):
    """Interface served by the CPU state object."""

    @property
    def is_terminator(self) -> bool:
        return False

    @property
    def declaration(self) -> str:
        from cpp.func import Func

        return Func.from_env(self.func).declaration

    @property
    def definition(self) -> str:
        return ""


class MemInterface(Interface):
    """Interface served by memory, independent of the CPU model."""

    @property
    def is_terminator(self) -> bool:
        return False


class ReadMem(MemInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"read<{OperandType.gen(out.width)}>({inputs[0]})"


class WriteMem(MemInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"write<{OperandType.gen(inputs[1].width)}>({inputs[0]}, {inputs[1]})"


class GetPC(CpuInterface):
    def __init__(self, func, **attributes):
        super().__init__(func, **attributes)
        self.pc = attributes[PC_ATTRIBUTE]
        self.attributes = attributes.keys()

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{self.name}()"

    @property
    def declaration(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"{t} {self.name}() const;"

    @property
    def definition(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"{t} CPU::{self.name}() const {{ return m_{self.pc.name}; }}\n"


class SetPC(CpuInterface):
    def __init__(self, func, **attributes):
        super().__init__(func, **attributes)
        self.pc = attributes[PC_ATTRIBUTE]
        self.attributes = attributes.keys()

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{self.name}({inputs[0]})"

    @property
    def is_terminator(self) -> bool:
        return True

    @property
    def definition(self) -> str:
        t = OperandType.gen(self.pc.width)
        return (
            f"void CPU::{self.name}(const {t} value) {{ m_{self.pc.name} = value; }}\n"
        )


class SysCall(CpuInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{self.name}()"

    @property
    def is_terminator(self) -> bool:
        return True

    @property
    def definition(self) -> str:
        return ""


m_cpu = Context(name="m_cpu", _type="CPU")
m_mem = Context(name="m_mem", _type="Memory")

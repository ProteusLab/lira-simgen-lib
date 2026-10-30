# lira-simgen-lib/interpreter/interface.py

from typing import List, Optional

from lib.attributes import PC_ATTRIBUTE
from lib.interface import Interface

from cpp.types import OperandType

from interpreter import config


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
    def __init__(self, func, **linked):
        super().__init__(func, **linked)
        self.width: int = self.outputs[0]

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        t = OperandType.gen(self.width)
        return f"{out} = {config.SimpleInterpConfig.M_MEM}.read<{t}>({inputs[0]});"

    @property
    def definition(self) -> str:
        return ""


class WriteMem(MemInterface):
    def __init__(self, func, **linked):
        super().__init__(func, **linked)
        self.width: int = self.inputs[1]

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        t = OperandType.gen(self.width)
        return (
            f"{config.SimpleInterpConfig.M_MEM}.write<{t}>({inputs[0]}, {inputs[1]});"
        )

    @property
    def definition(self) -> str:
        return ""


class GetPC(CpuInterface):
    def __init__(self, func, **attributes):
        super().__init__(func, **attributes)
        self.pc = attributes[PC_ATTRIBUTE]
        self.attributes = attributes.keys()

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{out} = {config.SimpleInterpConfig.M_CPU}.{self.name}();"

    @property
    def declaration(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"{t} {self.name}() const;"

    @property
    def definition(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"""{t} CPU::{self.name}() const {{ return m_{self.pc.name}; }}\n"""


class SetPC(CpuInterface):
    def __init__(self, func, **attributes):
        super().__init__(func, **attributes)
        # PC metadata constructed by the register-file model.
        self.pc = attributes[PC_ATTRIBUTE]
        self.attributes = attributes.keys()

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{config.SimpleInterpConfig.M_CPU}.{self.name}({inputs[0]});"

    @property
    def is_terminator(self) -> bool:
        return True

    @property
    def definition(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"""void CPU::{self.name}(const {t} value) {{ m_{self.pc.name} = value; }}\n"""


class SysCall(CpuInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{config.SimpleInterpConfig.M_CPU}.{self.name}();"

    @property
    def is_terminator(self) -> bool:
        return True

    @property
    def definition(self) -> str:
        return ""

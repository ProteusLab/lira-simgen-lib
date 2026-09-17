# lira-simgen-lib/interpreter/interface.py

from typing import List, Optional

from lib.interface import CpuInterface, MemInterface
from lib.types import OperandType

from interpreter import config


class ReadMem(MemInterface):
    def __init__(self, func, **linked):
        super().__init__(func, **linked)
        self.width: int = self.outputs[0]

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        t = OperandType.gen(self.width)
        return f"{out} = {config.SimpleInterpConfig.MEM_VAR}.read<{t}>({inputs[0]});"

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
            f"{config.SimpleInterpConfig.MEM_VAR}"
            f".write<{t}>({inputs[0]}, {inputs[1]});"
        )

    @property
    def definition(self) -> str:
        return ""


class GetPC(CpuInterface):
    def __init__(self, func, **attributes):
        super().__init__(func, **attributes)
        self.pc = attributes["pc"]
        self.attributes = attributes.keys()

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{out} = {config.SimpleInterpConfig.CPU_VAR}.{self.name}();"

    @property
    def declaration(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"{t} {self.name}() const;"

    @property
    def definition(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"""\
  // Read PC function
  {t} CPU::{self.name}() const {{
    return m_{self.pc.name};
  }}
"""


class SetPC(CpuInterface):
    def __init__(self, func, **attributes):
        super().__init__(func, **attributes)
        # PC metadata constructed by the register-file model.
        self.pc = attributes["pc"]
        self.attributes = attributes.keys()

    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.{self.name}({inputs[0]});"

    @property
    def definition(self) -> str:
        t = OperandType.gen(self.pc.width)
        return f"""\
  // Set PC function
  void CPU::{self.name}(const {t} value) {{
    m_{self.pc.name} = value;
  }}
"""


class SysCall(CpuInterface):
    def __call__(self, inputs, out: Optional[str] = None) -> str:
        return f"{config.SimpleInterpConfig.CPU_VAR}.{self.name}();"

    @property
    def definition(self) -> str:
        return ""

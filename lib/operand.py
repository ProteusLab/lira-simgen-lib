# lira-simgen-lib/simgen/operand.py

from typing import Optional

from lira.arch import Snippet
from lira.arch_utils import ArchIndex

from lib.regfile import IRegFile
from lib.types import OperandType


class Variable:
    def __init__(self, name: str, width: int):
        self.name: str = name
        self.width: int = width

    def __str__(self) -> str:
        return self.name

    @property
    def type(self) -> str:
        return OperandType.gen(self.width)

    @property
    def definition(self) -> str:
        return f"{self.type} {self.name}{{0}};"


class Constant(Variable):
    def __init__(self, name: str, width: int, value: str):
        super().__init__(name, width)
        self.value: str = value

    def __str__(self) -> str:
        return self.definition

    @property
    def definition(self) -> str:
        return f"{self.type} {self.name} = {self.value};"


class Operand(Variable):
    def __init__(self, name: str, width: int, index: ArchIndex, snippet: Snippet):
        super().__init__(name, width)
        self.index: ArchIndex = index
        self.snippet: Snippet = snippet


class Register(Operand):
    def __init__(
        self,
        name: str,
        width: int,
        index: ArchIndex,
        snippet: Snippet,
        src_pos: Optional[int] = None,
        dst_pos: Optional[int] = None,
        rf: Optional[IRegFile] = None,
    ):
        super().__init__(name, width, index, snippet)
        self.src_pos: Optional[int] = src_pos
        self.dst_pos: Optional[int] = dst_pos
        self.rf: Optional[IRegFile] = rf

    def read(self, var: Variable) -> str:
        return self.rf.read(self, var)

    def write(self, value: Variable) -> str:
        return self.rf.write(self, value)

    def wiring(self) -> str:
        if self.rf is None:
            return ""
        return self.rf.wiring(self)


class PC:
    def __init__(self, name: str, width: int, rf_name: Optional[str] = None):
        self.name: str = name
        self.width: int = width
        self.rf_name: Optional[str] = rf_name

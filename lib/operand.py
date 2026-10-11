# lira-simgen-lib/simgen/operand.py

from typing import Optional

from lira.arch import Snippet

from lib.regfile import IRegFile
from lib.types import Lanes, OperandType


class Variable:
    """A value; the result of a vector statement has `lanes` > 1 or, for a
    scalable shape, `lanes` times the multiplier `mult` lanes."""

    def __init__(self, name: str, width: int, lanes: int = 1, mult: Optional[str] = None):
        self.name: str = name
        self.width: int = width
        self.lanes: int = lanes
        self.mult: Optional[str] = mult

    def __str__(self) -> str:
        return self.name

    @property
    def is_vector(self) -> bool:
        return self.lanes > 1 or self.mult is not None

    @property
    def count(self) -> str:
        """C++ expression of the number of lanes."""
        return Lanes.count(self.lanes, self.mult)

    @property
    def type(self) -> str:
        return OperandType.vector(self.width, self.lanes, self.mult)

    @property
    def definition(self) -> str:
        if self.mult is not None:
            t = OperandType.gen(self.width)
            return f"{self.type} {self.name} = prot::vec::make<{t}>({self.count});"
        return f"{self.type} {self.name}{{0}};"


class Constant(Variable):
    def __init__(self, name: str, width: int, value: str, lanes: int = 1,
                 mult: Optional[str] = None):
        super().__init__(name, width, lanes, mult)
        self.value: str = value

    @property
    def definition(self) -> str:
        literal = OperandType.literal(int(self.value), self.width)
        if self.is_vector:
            t = OperandType.gen(self.width)
            return f"{super().definition}\nprot::vec::splat({self.name}, {t}{{{literal}}});"
        return f"{self.type} {self.name} = {literal};"


class LaneView(Variable):
    """Lane `index` of a variable, inside a loop over the lanes of a vector
    statement (defined by the loop, not by the node using it)."""

    def __init__(self, var: Variable, index: str):
        super().__init__(f"prot::vec::lane({var.name}, {index})", var.width)

    @property
    def definition(self) -> str:
        return ""


class Register(Variable):
    def __init__(
        self,
        name: str,
        width: int,
        snippet: Snippet,
        src_pos: Optional[int] = None,
        dst_pos: Optional[int] = None,
        rf: Optional[IRegFile] = None,
    ):
        super().__init__(name, width)
        self.snippet: Snippet = snippet
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

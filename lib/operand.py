# lira-simgen-lib/lib/operand.py
# Operand model for LIRA IR

from typing import Optional

from lira.arch import Snippet

from lib.regfile import IRegFile


class Variable:
    def __init__(self, name: str, width: int):
        self.name: str = name
        self.width: int = width

    def __str__(self) -> str:
        return self.name


class Constant(Variable):
    def __init__(self, name: str, width: int, value: str):
        super().__init__(name, width)
        self.value: str = value


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


class PC:
    def __init__(self, name: str, width: int, rf_name: Optional[str] = None):
        self.name: str = name
        self.width: int = width
        self.rf_name: Optional[str] = rf_name

# lira-simgen-lib/cpp/context.py

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from lib.operand import Variable

from cpp.types import OperandType


@dataclass
class Context:
    M_CTX = "ctx"

    name: str
    fields: List[Variable]

    @classmethod
    def union(cls, ctxs: Iterable[Optional["Context"]]) -> Optional["Context"]:
        name = None
        fields = {}

        for ctx in ctxs:
            if ctx is None:
                continue
            if name is None:
                name = ctx.name
            for field in ctx.fields:
                fields.setdefault(field.name, field)

        return None if name is None else cls(name=name, fields=list(fields.values()))

    def initializer(self, value_of: Callable[[str], int]) -> str:
        fields = ", ".join(
            f".{field.name} = {value_of(field.name)}" for field in self.fields
        )
        return f"{self.name}{{{fields}}}"

    @property
    def param(self) -> str:
        return f"const {self.name}& {self.M_CTX}"

    @property
    def declaration(self) -> str:
        members = "\n".join(
            f"{OperandType.gen(field.width)} {field.name};" for field in self.fields
        )
        return f"""struct {self.name} {{
{members}
}};
"""

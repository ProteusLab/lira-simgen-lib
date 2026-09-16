# lira-simgen-lib/lib/cpp/func.py

from dataclasses import dataclass
from typing import List

from lira.arch_utils import ArchIndex
from lira.ir_std import StmtInput

from lib.builders import ConstraintBuilder
from lib.config import IConfig
from lib.nodes import Return, render_nodes
from lib.operand import Variable
from lib.types import OperandType


def _letter_params(widths: List[int], offset: int = 0) -> List[Variable]:
    return [
        Variable(chr(ord("a") + offset + i), w)
        for i, w in enumerate(widths)
    ]


@dataclass
class Func:
    name: str
    ret: str
    params: List[Variable]
    body: str

    @classmethod
    def from_op(cls, op) -> "Func":
        body_fn = getattr(type(op), "_cpp_body", None)
        if body_fn is None:
            raise ValueError(f"No C++ body defined for operation {op.name}")
        name = op.semantic_func or op.name
        return cls(name, OperandType.gen(op.outputs[0]),
                   _letter_params(op.inputs), body_fn(op))

    @classmethod
    def from_env(cls, env) -> "Func":
        ret = OperandType.gen(env.outputs[0]) if env.outputs else "void"
        return cls(env.name, ret, _letter_params(env.inputs), "")

    @classmethod
    def from_snippet(cls, snippet, index: ArchIndex) -> "Func":
        mach_inst = IConfig.mach_inst
        input_stmts = [
            stmt for stmt in snippet.seq.stmts
            if stmt.kind == StmtInput.kind and int(stmt.specifier) != 0
        ]
        params = [mach_inst] + _letter_params(
            [stmt.outputs_types[0] for stmt in input_stmts]
        )

        nodes = ConstraintBuilder(
            index, params=params
        ).build(snippet.seq)
        body = render_nodes(nodes)
        ret_node = next(n for n in nodes if isinstance(n, Return))
        return cls(snippet.name, OperandType.gen(ret_node.value.width),
                   params, body)

    def __call__(self, args: List[str]) -> str:
        """Emit a call expression of this function."""
        return f"{self.name}({', '.join(args)})"

    @property
    def declaration(self) -> str:
        params = ", ".join(f"{p.type} {p.name}" for p in self.params)
        return f"{self.ret} {self.name}({params});"

    @property
    def definition(self) -> str:
        params = ", ".join(f"{p.type} {p.name}" for p in self.params)
        return f"{self.ret} {self.name}({params})\n{{\n{self.body}\n}}"

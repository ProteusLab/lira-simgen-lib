# lira-simgen-lib/cpp/func.py

from dataclasses import dataclass
from typing import List

from lira.arch_utils import ArchIndex
from lira.ir_std import StmtInput

from lib.builders import CodeBuilder
from lib.config import IConfig
from lib.nodes import render_nodes
from lib.operand import Variable
from lib.snippet import SnippetKind

import cpp.nodes  # noqa: F401  (registers the node renderers)

from cpp.types import OperandType


def _letter_params(widths: List[int], offset: int = 0) -> List[Variable]:
    return [Variable(chr(ord("a") + offset + i), w) for i, w in enumerate(widths)]


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
        return cls(
            name, OperandType.gen(op.outputs[0]), _letter_params(op.inputs), body_fn(op)
        )

    @classmethod
    def from_env(cls, env) -> "Func":
        ret = OperandType.gen(env.outputs[0]) if env.outputs else "void"
        return cls(env.name, ret, _letter_params(env.inputs), "")

    @classmethod
    def from_snippet(cls, snippet, index, kind, param_names=None):
        mach_inst = IConfig.mach_inst
        input_stmts = [
            stmt for stmt in snippet.seq.stmts if stmt.kind == StmtInput.kind
        ]
        if kind is SnippetKind.ENCODE:
            named = input_stmts
            prefix = []
        elif kind in (SnippetKind.DECODE, SnippetKind.CONSTRAINT):
            # Input 0 is the machine word by definition.
            named = [stmt for stmt in input_stmts if int(stmt.specifier) != 0]
            prefix = [mach_inst]
        else:
            raise ValueError(f"unexpected snippet kind: {kind!r}")

        widths = [stmt.outputs_types[0] for stmt in named]
        if param_names is None:
            params = prefix + _letter_params(widths)
        else:
            if len(param_names) != len(named):
                raise ValueError(
                    f"snippet '{snippet.name}' takes {len(named)} inputs, "
                    f"expected {len(param_names)} operands"
                )
            params = prefix + [
                Variable(name, width) for name, width in zip(param_names, widths)
            ]

        builder = CodeBuilder(index, params=params)
        nodes = builder.build(snippet.seq)
        body = render_nodes(nodes)
        if builder.ret is None:
            raise ValueError(f"snippet '{snippet.name}' has no output statement")
        return cls(snippet.name, OperandType.gen(builder.ret.width), params, body)

    def __call__(self, args: List[str]) -> str:
        return f"{self.name}({', '.join(args)})"

    @property
    def param_list(self) -> str:
        return ", ".join(f"{OperandType.gen(p.width)} {p.name}" for p in self.params)

    @property
    def declaration(self) -> str:
        return f"{self.ret} {self.name}({self.param_list});"

    @property
    def definition(self) -> str:
        return f"""
{self.ret} {self.name}({self.param_list})
{{
    {self.body}
}}
"""

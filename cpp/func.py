# lira-simgen-lib/cpp/func.py

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from lira.arch import Snippet
from lira.arch_utils import ArchIndex
from lira.ir import Statement
from lira.ir_std import StmtInput

from lib.builders import CodeBuilder
from lib.nodes import render_nodes
from lib.operand import Variable

import cpp.nodes

from cpp.context import BaseContext
from cpp.types import OperandType


@dataclass
class Func:
    name: str
    ret: str
    params: List[Variable]
    body: str
    ctx: Optional[BaseContext] = None

    @staticmethod
    def _arg_params(widths: List[int]) -> List[Variable]:
        return [Variable(f"arg{i}", w) for i, w in enumerate(widths)]

    @classmethod
    def from_op(cls, op) -> "Func":
        body_fn = getattr(type(op), "_cpp_body", None)
        if body_fn is None:
            raise ValueError(f"No C++ body defined for operation {op.name}")
        name = op.semantic_func or op.name

        return cls(
            name=name,
            ret=OperandType.gen(op.outputs[0]),
            params=cls._arg_params(op.inputs),
            body=body_fn(op),
        )

    @classmethod
    def from_env(cls, env) -> "Func":
        ret = OperandType.gen(env.outputs[0]) if env.outputs else OperandType.VOID
        return cls(name=env.name, ret=ret, params=cls._arg_params(env.inputs), body="")

    @classmethod
    def _inputs(cls, snippet: Snippet) -> List[Statement]:
        return [stmt for stmt in snippet.seq.stmts if stmt.kind == StmtInput.kind]

    @classmethod
    def _params(cls, snippet: Snippet, param_names=None) -> List[Variable]:
        inputs = cls._inputs(snippet)

        widths = [stmt.outputs_types[0] for stmt in inputs]
        if param_names is None:
            return cls._arg_params(widths)

        if len(param_names) != len(inputs):
            raise ValueError(
                f"snippet '{snippet.name}' takes {len(inputs)} inputs, "
                f"expected {len(param_names)} operands"
            )
        return [Variable(name, width) for name, width in zip(param_names, widths)]

    @classmethod
    def _build_snippet(
        cls,
        snippet: Snippet,
        index: ArchIndex,
        params: List[Variable],
        ctx: Optional[BaseContext] = None,
    ) -> "Func":
        builder = CodeBuilder(index, inputs=params)
        nodes = builder.build(snippet.seq)

        body = render_nodes(nodes, ctx=ctx)
        if builder.ret is None:
            raise ValueError(f"snippet '{snippet.name}' has no output statement")

        return cls(
            name=snippet.name,
            ret=OperandType.gen(builder.ret.width),
            params=params,
            body=body,
            ctx=ctx,
        )

    @classmethod
    def from_snippet(
        cls,
        snippet: Snippet,
        index: ArchIndex,
        param_names=None,
        ctx: Optional[BaseContext] = None,
    ) -> "Func":
        params = cls._params(snippet, param_names)
        return cls._build_snippet(snippet, index, params, ctx)

    def __call__(self, *args: object) -> str:
        return f"{self.name}({', '.join(str(arg) for arg in args)})"

    @property
    def param_list(self) -> str:
        return ", ".join(f"{OperandType.gen(p.width)} {p.name}" for p in self.params)

    @property
    def signature(self) -> str:
        parts = [self.ctx.param] if self.ctx is not None else []
        parts.append(self.param_list)
        return ", ".join(p for p in parts if p)

    @property
    def declaration(self) -> str:
        return f"{self.ret} {self.name}({self.signature});"

    @property
    def definition(self) -> str:
        return f"""
{self.ret} {self.name}({self.signature})
{{
{self.body}
}}
"""


def snippet_func(
    index: ArchIndex, name: str, ctx: Optional[BaseContext] = None
) -> Func:
    return Func.from_snippet(snippet=index.snippet[name], index=index, ctx=ctx)


def snippet_funcs(
    index: ArchIndex, names: Iterable[str], ctx: Optional[BaseContext] = None
) -> Dict[str, Func]:
    return {name: snippet_func(index, name, ctx) for name in dict.fromkeys(names)}

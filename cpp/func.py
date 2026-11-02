# lira-simgen-lib/cpp/func.py

from dataclasses import dataclass
from typing import List

from lira.arch_utils import ArchIndex
from lira.ir_std import StmtInput

from lib.builders import CodeBuilder
from lib.nodes import render_nodes
from lib.operand import Variable

import cpp.nodes

from cpp.types import OperandType


@dataclass
class Func:
    name: str
    ret: str
    params: List[Variable]
    body: str

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
            name,
            OperandType.gen(op.outputs[0]),
            cls._arg_params(op.inputs),
            body_fn(op),
        )

    @classmethod
    def from_env(cls, env) -> "Func":
        ret = OperandType.gen(env.outputs[0]) if env.outputs else "void"
        return cls(env.name, ret, cls._arg_params(env.inputs), "")

    @classmethod
    def _params(cls, snippet, param_names=None):
        inputs = []
        for stmt in snippet.seq.stmts:
            if stmt.kind == StmtInput.kind:
                inputs.append(stmt)

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
    def _build_snippet(cls, snippet, index, params):
        builder = CodeBuilder(index, params=params)
        nodes = builder.build(snippet.seq)
        body = render_nodes(nodes)
        if builder.ret is None:
            raise ValueError(f"snippet '{snippet.name}' has no output statement")
        return cls(snippet.name, OperandType.gen(builder.ret.width), params, body)

    @classmethod
    def from_snippet(cls, snippet, index, param_names=None):
        params = cls._params(snippet, param_names)
        return cls._build_snippet(snippet, index, params)

    @classmethod
    def from_encode_snippet(cls, snippet, index, param_names=None):
        params = cls._params(snippet, param_names)
        return cls._build_snippet(snippet, index, params)

    @classmethod
    def from_decode_snippet(cls, snippet, index):
        params = cls._params(snippet)
        return cls._build_snippet(snippet, index, params)

    @classmethod
    def from_constraint_snippet(cls, snippet, index):
        params = cls._params(snippet)
        return cls._build_snippet(snippet, index, params)

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

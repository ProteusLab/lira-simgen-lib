# lira-simgen-lib/lib/cpp/func.py

from dataclasses import dataclass
from typing import List

from lira.arch_utils import ArchIndex
from lira.ir_std import StmtInput

from lib.builders import CodeBuilder
from lib.nodes import Return, render_nodes
from lib.operand import Variable
from lib.types import OperandType


def _letter_params(widths: List[int], offset: int = 0) -> List[Variable]:
    return [Variable(chr(ord("a") + offset + i), w) for i, w in enumerate(widths)]


def _masked(body: str, width: int, ret: str) -> str:
    """Wrap an operation body so that the result keeps only `width` bits:
    C++ types are rounded up to standard widths (and `~` on bool is not a
    1-bit NOT)."""
    wide = OperandType.gen(max(width, 8))
    mask = OperandType.literal((1 << width) - 1, width)
    return f"""  const {wide} r = [&]() -> {wide} {{
{body}
  }}();
  return ({ret})(r & {mask});"""


@dataclass
class Func:
    name: str
    ret: str
    params: List[Variable]
    body: str

    @classmethod
    def from_op(cls, op) -> "Func":
        ret = OperandType.tuple(op.outputs)
        if op.semantic_func:
            # Defined by a snippet (emitted with the other snippets)
            return cls(op.semantic_func, ret, _letter_params(op.inputs), "")
        body_fn = getattr(type(op), "_cpp_body", None)
        if body_fn is None:
            raise ValueError(f"No C++ body defined for operation {op.name}")
        body = body_fn(op)
        if not OperandType.is_exact(op.outputs[0]):
            body = _masked(body, op.outputs[0], ret)
        return cls(op.name, ret, _letter_params(op.inputs), body)

    @classmethod
    def from_env(cls, env) -> "Func":
        ret = OperandType.gen(env.outputs[0]) if env.outputs else "void"
        return cls(env.name, ret, _letter_params(env.inputs), "")

    @classmethod
    def from_snippet(cls, snippet, index: ArchIndex) -> "Func":
        inputs = {
            int(stmt.specifier): stmt.outputs_types[0]
            for stmt in snippet.seq.stmts
            if stmt.kind == StmtInput.kind
        }
        params = _letter_params([inputs[i] for i in range(len(inputs))])

        nodes = CodeBuilder(index, params=params).build(snippet.seq)
        body = render_nodes(nodes)
        ret_node = next(n for n in nodes if isinstance(n, Return))
        ret = OperandType.tuple([v.width for v in ret_node.values])
        return cls(snippet.name, ret, params, body)

    def __call__(self, args: List[str]) -> str:
        return f"{self.name}({', '.join(args)})"

    @property
    def declaration(self) -> str:
        params = ", ".join(f"{p.type} {p.name}" for p in self.params)
        return f"{self.ret} {self.name}({params});"

    @property
    def definition(self) -> str:
        params = ", ".join(f"{p.type} {p.name}" for p in self.params)
        return f"{self.ret} {self.name}({params})\n{{\n{self.body}\n}}"

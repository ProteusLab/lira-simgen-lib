"""Lower LIRA syntax snippets to C++ formatter helpers.

CodeBuilder handles input, const, and op. Their C++ renderers are registered
by cpp.nodes when cpp.func is imported.
"""

from dataclasses import dataclass

from cpp.func import Func
from cpp.types import OperandType
from lib.builders import CodeBuilder, StmtHandler, serves
from lib.nodes import NodeImpl, render_nodes
from lib.operand import Variable


class FormatBuilder(CodeBuilder):
    # Syntax statement handlers

    @serves("string")
    class StringHandler(StmtHandler):
        def build(self) -> None:
            self.builder.nodes.append(String(self.stmt.specifier))

    @serves("dyn_string")
    class DynString(StmtHandler):
        def build(self) -> None:
            if self.stmt.specifier != "mnemonic":
                raise ValueError(f"Unsupported dyn_string specifier '{self.stmt.specifier}'")
            self.builder.nodes.append(Mnemonic())

    @serves("whitespace")
    class Whitespace(StmtHandler):
        def build(self) -> None:
            self.builder.nodes.append(String(" "))

    @serves("table")
    class TableHandler(StmtHandler):
        def build(self) -> None:
            table = self.builder.index.tables_str[self.stmt.specifier]
            index = self.builder.resolve_var(self.stmt.inputs[0])
            self.builder.nodes.append(Table(table.name, index))

    @serves("format")
    class FormatHandler(StmtHandler):
        def build(self) -> None:
            if self.stmt.specifier != "dec":
                raise ValueError(f"Unsupported format specifier '{self.stmt.specifier}'")
            value = self.builder.resolve_var(self.stmt.inputs[0])
            self.builder.nodes.append(Decimal(value))

    # C++ helper construction

    @classmethod
    def snippet_func(cls, snippet, index) -> Func:
        widths = {}
        for stmt in Func._inputs(snippet):
            operand = int(stmt.specifier)
            width = stmt.outputs_types[0]
            if operand < 0 or widths.setdefault(operand, width) != width:
                raise ValueError(f"Invalid input {operand} in snippet '{snippet.name}'")

        # The formatter passes the operand prefix through the last referenced slot.
        params = Func._arg_params(
            [widths.get(operand, 32) for operand in range(max(widths, default=-1) + 1)]
        )
        nodes = cls(index, params).build(snippet.seq)
        body = "\n".join((render_nodes(nodes), "  return std::move(ctx.output);"))
        return Func(snippet.name, "std::string", params, body)


# C++ renderers for syntax nodes


@dataclass
class String:
    value: str


@NodeImpl.serves(String)
def render_string(node: String) -> str:
    return f"  ctx.output += {string_view_literal(node.value)};"


@dataclass
class Mnemonic:
    pass


@NodeImpl.serves(Mnemonic)
def render_mnemonic(node: Mnemonic) -> str:
    return "  ctx.output += ctx.mnemonic;"


@dataclass
class Table:
    name: str
    index: Variable


@NodeImpl.serves(Table)
def render_table(node: Table) -> str:
    return f"  ctx.output += string_tables::{node.name}.at({node.index});"


@dataclass
class Decimal:
    value: Variable


@NodeImpl.serves(Decimal)
def render_decimal(node: Decimal) -> str:
    value = node.value
    if value.width not in (8, 16, 32, 64):
        raise ValueError(f"Unsupported decimal operand width {value.width}")
    signed_type = OperandType.gen(value.width, signed=True)
    return f"  ctx.output += std::to_string(static_cast<{signed_type}>({value}));"


# String literals shared with the emitter's table definitions


def string_view_literal(text: str) -> str:
    value = text.encode("utf-8")
    literal = "".join(
        chr(byte) if 32 <= byte < 127 and byte not in (34, 92) else f"\\{byte:03o}"
        for byte in value
    )
    return f'std::string_view{{"{literal}", {len(value)}}}'

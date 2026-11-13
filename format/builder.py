"""Lower LIRA syntax snippets to C++ formatter helpers."""

from lira.ir import Statement

from cpp.emitter import StatementEmitter
from cpp.func import Func
from cpp.types import OperandType


class FormatBuilder(StatementEmitter):
    def emit_string(self, stmt: Statement) -> str:
        return f"  ctx.output += {string_view_literal(stmt.specifier)};"

    def emit_dyn_string(self, stmt: Statement) -> str:
        if stmt.specifier != "mnemonic":
            raise ValueError(f"Unsupported dyn_string specifier '{stmt.specifier}'")
        return "  ctx.output += ctx.mnemonic;"

    def emit_whitespace(self, stmt: Statement) -> str:
        return f'  ctx.output += {string_view_literal(" ")};'

    def emit_table(self, stmt: Statement) -> str:
        table = self.index.tables_str[stmt.specifier]
        index = self.resolve_var(stmt.inputs[0])
        return f"  ctx.output += string_tables::{table.name}.at({index});"

    def emit_format(self, stmt: Statement) -> str:
        if stmt.specifier != "dec":
            raise ValueError(f"Unsupported format specifier '{stmt.specifier}'")
        value = self.resolve_var(stmt.inputs[0])
        if value.width not in (8, 16, 32, 64):
            raise ValueError(f"Unsupported decimal operand width {value.width}")
        signed_type = OperandType.gen(value.width, signed=True)
        return f"  ctx.output += std::to_string(static_cast<{signed_type}>({value}));"

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
        statements = cls(index, params).render(snippet.seq)
        body = "\n".join((statements, "  return std::move(ctx.output);"))
        return Func(snippet.name, "std::string", params, body)


def string_view_literal(text: str) -> str:
    value = text.encode("utf-8")
    literal = "".join(
        chr(byte) if 32 <= byte < 127 and byte not in (34, 92) else f"\\{byte:03o}"
        for byte in value
    )
    return f'std::string_view{{"{literal}", {len(value)}}}'

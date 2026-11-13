from lira.ir import Statement

from shared.cli import default_parser
from shared.emitter import ContextBase, Emitter, context, emit
from shared.types import OperandType


@context(name="FormatContext")
class FormatterContext(ContextBase):
    cfg = "const FmtConfig&"
    output = "std::string"
    mnemonic = "std::string_view"

    @emit("string")
    def append_string(self, ctx, stmt: Statement, specifier: str) -> str:
        return f"{ctx.output} += {string_literal(specifier)};"

    @emit("dyn_string", "mnemonic")
    def append_mnemonic(self, ctx, stmt: Statement) -> str:
        return f"{ctx.output} += {ctx.mnemonic};"

    @emit("whitespace", "_")
    def append_whitespace(self, ctx, stmt: Statement) -> str:
        return f"{ctx.output} += ' ';"

    @emit("table")
    def append_table_entry(self, ctx, stmt: Statement, specifier: str) -> str:
        index = self.resolve_var(stmt.inputs[0])
        return f"{ctx.output} += string_tables::{specifier}.at({index});"

    @emit("format", "dec")
    def append_decimal(self, ctx, stmt: Statement) -> str:
        value = self.resolve_var(stmt.inputs[0])
        signed_type = OperandType.gen(value.width, signed=True)
        return f"{ctx.output} += std::to_string(static_cast<{signed_type}>({value}));"


def main() -> None:
    parser = default_parser(__file__)
    args = parser.parse_args()
    emitter = Emitter.from_args(args, ctx=FormatterContext())
    snippet_names = emitter.collect_snippet_names(
        lambda instr: [syntax.condition for syntax in instr.syntaxes],
        lambda instr: [syntax.syntax for syntax in instr.syntaxes],
    )
    emitter.args.snippet_functions = emitter.compile_snippets(snippet_names)
    emitter.args.string_tables = emitter.arch.tables_str
    emitter.args.string_literal = string_literal
    emitter.emit()


def string_literal(text: str) -> str:
    value = text.encode("utf-8")
    literal = "".join(
        chr(byte) if 32 <= byte < 127 and byte not in (34, 92) else f"\\{byte:03o}"
        for byte in value
    )
    return f'std::string_view{{"{literal}", {len(value)}}}'


if __name__ == "__main__":
    main()

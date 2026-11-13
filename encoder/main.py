from lira.ir import Statement

from shared.cli import default_parser
from shared.emitter import ContextBase, Emitter, context, emit


@context(name="EncodeContext")
class EncoderContext(ContextBase):
    const_encoding_part = "uint32_t"

    def initializer(self, encoding) -> str:
        return super().initializer(const_encoding_part=encoding.const_encoding_part)

    @emit("dyn_const", "const_encoding_part")
    def read_encoding_part(self, ctx, stmt: Statement) -> str:
        return self.init_with(stmt, ctx.const_encoding_part)


def main() -> None:
    parser = default_parser(__file__)
    args = parser.parse_args()
    emitter = Emitter.from_args(args, ctx=EncoderContext())
    snippet_names = emitter.collect_snippet_names(lambda instr: (instr.encoding.encode,))
    emitter.args.snippet_functions = emitter.compile_snippets(snippet_names)
    emitter.emit()


if __name__ == "__main__":
    main()

from lira.ir import Statement

from shared import cpp
from shared.cli import default_parser
from shared.context import BaseContext, context, emit
from shared.emitter import Emitter


@context(name="DecodeContext")
class DecoderContext(BaseContext):
    const_mask = "uint32_t"
    const_encoding_part = "uint32_t"

    def initializer(self, encoding) -> str:
        return super().initializer(
            const_mask=encoding.const_mask,
            const_encoding_part=encoding.const_encoding_part,
        )

    @emit("dyn_const", "const_mask")
    def read_mask(self, ctx, stmt: Statement) -> cpp.Statement:
        return self.init_with(stmt, ctx.const_mask)

    @emit("dyn_const", "const_encoding_part")
    def read_encoding_part(self, ctx, stmt: Statement) -> cpp.Statement:
        return self.init_with(stmt, ctx.const_encoding_part)


def main() -> None:
    parser = default_parser(__file__)
    args = parser.parse_args()
    emitter = Emitter.from_args(args, ctx=DecoderContext())
    snippet_names = emitter.collect_snippet_names(
        lambda instr: (instr.encoding.constraint_decode,),
        lambda instr: instr.encoding.decode,
    )
    emitter.args.snippet_functions = emitter.compile_snippets(snippet_names)
    emitter.emit()


if __name__ == "__main__":
    main()

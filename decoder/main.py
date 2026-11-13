from lira.ir import Statement

from shared.cli import default_parser
from shared.emitter import ContextBase, Emitter, context, emit


@context(name="DecodeContext")
class DecoderContext(ContextBase):
    const_mask = "uint32_t"
    const_encoding_part = "uint32_t"

    @emit("dyn_const", "const_mask")
    def read_mask(self, ctx, stmt: Statement) -> str:
        return self.init_with(stmt, ctx.const_mask)

    @emit("dyn_const", "const_encoding_part")
    def read_encoding_part(self, ctx, stmt: Statement) -> str:
        return self.init_with(stmt, ctx.const_encoding_part)


def main() -> None:
    parser = default_parser(__file__)
    args = parser.parse_args()
    emitter = Emitter.from_args(args, emit_isa=True, ctx=DecoderContext())
    snippet_names = emitter.collect_snippet_names(
        lambda instr: (instr.encoding.constraint_decode,),
        lambda instr: instr.encoding.decode,
    )
    emitter.args.snippet_functions = emitter.compile_snippets(snippet_names)
    emitter.emit()


if __name__ == "__main__":
    main()

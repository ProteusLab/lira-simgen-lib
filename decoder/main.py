from lira.ir import Statement

from decoder.tree import MaskValue, build_tree
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
    parser.add_argument(
        "--dispatch", choices=("table", "switch"), default="table",
        help="How to traverse the generated decoder tree (default: table)",
    )
    args = parser.parse_args()
    emitter = Emitter.from_args(args, ctx=DecoderContext())
    snippet_names = emitter.collect_snippet_names(
        lambda instr: filter(None, (instr.encoding.constraint_decode,)),
        lambda instr: instr.encoding.decode,
    )
    emitter.args.snippet_functions = emitter.compile_snippets(snippet_names)
    emitter.args.dispatch = args.dispatch
    emitter.args.tree = build_tree([
        MaskValue(instr.encoding.const_mask, instr.encoding.const_encoding_part)
        for instr in emitter.arch.instructions
    ])
    emitter.args.node = cpp.Struct("Node", (
        cpp.NamedValue("shift", "unsigned"),
        cpp.NamedValue("mask", "prot::isa::Word"),
        cpp.NamedValue("offset", "std::size_t"),
    ))
    emitter.emit()


if __name__ == "__main__":
    main()

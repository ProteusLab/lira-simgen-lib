from interpreter.context import ExecuteContext
from interpreter.fpu import fpu_helpers
from interpreter.state import State
from shared import cpp
from shared.cli import default_parser
from shared.emitter import Emitter


def main() -> None:
    args = default_parser(__file__).parse_args()
    emitter = Emitter.from_args(args)
    state = State(emitter.arch, args.arch_target)
    emitter.ctx = ExecuteContext(state, emitter.operations)
    names = emitter.collect_snippet_names(lambda instr: (instr.semantic,))
    functions = emitter.compile_snippets(names)
    for name, snippet in functions.items():
        if any(stmt.shape.lanes_mult for stmt in emitter.snippets[name].seq.stmts):
            snippet.function.body.insert(
                0, cpp.Statement("prot::vec::ArenaScope arena_scope;")
            )
    emitter.args.state = state
    emitter.args.terminators = {
        name
        for name in names
        if any(
            stmt.kind == "env" and stmt.specifier in ("setPC", "sysCall")
            for stmt in emitter.snippets[name].seq.stmts
        )
    }
    emitter.args.snippet_functions = functions
    emitter.args.fpu_helpers = fpu_helpers(emitter.arch, state)
    emitter.emit()


if __name__ == "__main__":
    main()

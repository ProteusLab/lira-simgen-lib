from types import SimpleNamespace

from lira.arch_ser_yaml import read_arch

from shared._compile import CompiledSnippet, compile_snippet
from shared.isa import opcode_name
from shared.templates import render


class Emitter:
    def __init__(self, arch, template_dir, out_dir, ctx=None):
        self.arch = arch
        self.template_dir = template_dir
        self.out_dir = out_dir
        self.ctx = ctx
        self.args = SimpleNamespace()
        self.snippets = {snippet.name: snippet for snippet in arch.snippets}
        self.operations = {operation.name: operation for operation in arch.operations}

    @classmethod
    def from_args(cls, args, *, ctx=None):
        return cls(
            read_arch(args.ir_path),
            args.template_dir,
            args.out_dir,
            ctx=ctx,
        )

    def collect_snippet_names(self, *selectors) -> list[str]:
        names = (
            name
            for select in selectors
            for instruction in self.arch.instructions
            for name in select(instruction)
        )
        return list(dict.fromkeys(names))

    def compile_snippets(self, names, *, context_type=None) -> dict[str, CompiledSnippet]:
        """Compile each named snippet once for this emitter's usage.

        If the usage has a context struct, its parameter defaults to a const
        reference. context_type can supply the full C++ parameter type.
        """
        return {
            name: compile_snippet(
                self.snippets[name], self.operations, self.ctx, context_type=context_type
            )
            for name in dict.fromkeys(names)
        }

    def emit(self) -> None:
        instructions = self.arch.instructions
        values = dict(
            instructions=instructions,
            ctx=self.ctx,
            emit_functions=emit_functions,
            opcode_name=opcode_name,
            operand_args=operand_args,
            **vars(self.args),
        )
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for template in sorted(self.template_dir.glob("*.jinja")):
            content = render(self.template_dir, template.name, **values)
            (self.out_dir / template.stem).write_text(content, encoding="utf-8")


def emit_functions(functions) -> str:
    return "\n\n".join(
        snippet.function.definition() for snippet in functions.values()
    )


def operand_args(instruction: str, count: int) -> list[str]:
    return [f"{instruction}.operand{index}" for index in range(count)]

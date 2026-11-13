from copy import copy
from types import SimpleNamespace

from lira.arch_ser_yaml import read_arch

from shared.isa import opcode_name
from shared.snippet import compile_snippet, initialize_outputs
from shared.templates import render


def emit(kind, specifier=None):
    def decorate(method):
        method.statement_key = kind, specifier
        return method

    return decorate


def context(name):
    def decorate(cls):
        cls.fields = {
            key: value
            for key, value in vars(cls).items()
            if not key.startswith("_") and isinstance(value, str)
        }
        cls.handlers = {
            method.statement_key: method.__name__
            for method in vars(cls).values()
            if hasattr(method, "statement_key")
        }
        cls.name = name
        return cls

    return decorate


class ContextBinding:
    def __init__(self, name: str, fields: dict[str, str]):
        self._name = name
        self._fields = fields

    def __getattr__(self, field: str) -> str:
        if field not in self._fields:
            raise AttributeError(field)
        return f"{self._name}.{field}"


class ContextBase:
    parameter_name = "ctx"

    @property
    def declaration(self) -> str:
        fields = "\n".join(f"  {ty} {name};" for name, ty in self.fields.items())
        return f"struct {self.name} {{\n{fields}\n}};"

    def initializer(self, **values) -> str:
        fields = ", ".join(
            f".{field} = {values[field]}" for field in self.fields if field in values
        )
        unknown = values.keys() - self.fields.keys()
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown {self.name} fields: {names}")
        return f"{self.name}{{{fields}}}"

    def for_snippet(self, values):
        context = copy(self)
        context._values = values
        return context

    def resolve_var(self, name):
        return self._values[name]

    def init_with(self, stmt, *expressions) -> str:
        outputs = [self.resolve_var(name) for name in stmt.outputs]
        return initialize_outputs(outputs, expressions)

    def emit_statement(self, stmt):
        binding = ContextBinding(self.parameter_name, self.fields)
        exact = self.handlers.get((stmt.kind, stmt.specifier))
        if exact is not None:
            return getattr(self, exact)(binding, stmt)
        general = self.handlers.get((stmt.kind, None))
        if general is not None:
            return getattr(self, general)(binding, stmt, stmt.specifier)
        return None


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

    def compile_snippets(self, names):
        return {
            name: compile_snippet(self.snippets[name], self.operations, self.ctx)
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


def emit_functions(functions, context_type=None) -> str:
    return "\n\n".join(
        function.definition(context_type) for function in functions.values()
    )


def operand_args(instruction: str, count: int) -> list[str]:
    return [f"{instruction}.operand{index}" for index in range(count)]

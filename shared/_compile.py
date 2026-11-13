"""Lower LIRA snippets into C++ functions."""

from collections.abc import Mapping, Sequence
from copy import copy
from dataclasses import dataclass

from lira.arch import Operation, Snippet

from shared import cpp
from shared._values import cpp_value, initialize_outputs, is_vector
from shared.context import BaseContext
from shared.snippet import analyze_snippet


@dataclass
class CompiledSnippet:
    function: cpp.Function
    input_slots: tuple[int, ...]
    has_context: bool

    def call(self, operands: Sequence[str], *, ctx: str | None = None) -> str:
        """Render a call with operands selected by LIRA input index.

        If the snippet has a context parameter, ctx is the C++ expression
        to pass for it.
        """
        if self.has_context != (ctx is not None):
            raise ValueError(f"{self.function.name}: context argument does not match signature")
        arguments = [ctx] if ctx is not None else []
        arguments.extend(operands[index] for index in self.input_slots)
        return self.function.call(*arguments)


def compile_snippet(
    snippet: Snippet,
    operations: Mapping[str, Operation],
    usage: BaseContext | None = None,
    *,
    context_type: str | None = None,
) -> CompiledSnippet:
    """Compile a snippet using the supplied statement handlers and context."""
    info = analyze_snippet(snippet)
    values = {}
    emit_statement = _statement_emitter(usage, values) if usage is not None else None
    body = []
    for stmt in snippet.seq.stmts:
        args = [values[name] for name in stmt.inputs]
        results = [info.values[name] for name in stmt.outputs]
        values.update((value.name, value) for value in results)
        if stmt.kind == "input":
            code = initialize_outputs(results, [f"arg{int(stmt.specifier)}"])
        elif stmt.kind == "output":
            continue
        else:
            code = emit_statement(stmt) if emit_statement is not None else None
            if code is None:
                code = _emit_scalar(snippet.name, stmt, args, results, operations)
        body.append(cpp.Statement(code) if isinstance(code, str) else code)

    params = []
    has_context = usage is not None and usage.struct is not None
    if has_context:
        ty = context_type or f"const {usage.struct.name}&"
        params.append(cpp.NamedValue(usage.parameter_name, ty))
    elif context_type is not None:
        raise ValueError(f"{snippet.name}: context type supplied without a context")
    params.extend(
        cpp.NamedValue(f"arg{index}", cpp_value(value).type)
        for index, value in info.inputs.items()
    )

    outputs = [cpp_value(value) for value in info.outputs.values()]
    return_type = "void"
    if len(outputs) == 1:
        return_type = outputs[0].type
        body.append(cpp.Statement(f"return {outputs[0]};"))
    elif outputs:
        types = ", ".join(out.type for out in outputs)
        return_type = f"std::tuple<{types}>"
        body.append(cpp.Statement("return {" + ", ".join(map(str, outputs)) + "};"))

    function = cpp.Function(snippet.name, return_type, tuple(params), body)
    return CompiledSnippet(function, tuple(info.inputs), has_context)


def _emit_scalar(snippet_name, stmt, args, results, operations):
    if is_vector(stmt.shape):
        raise ValueError(f"{snippet_name}: unsupported shape for {stmt.kind}")
    if stmt.kind == "const":
        (out,) = results
        value = int(stmt.specifier, 0) % (1 << out.width)
        return initialize_outputs(results, [cpp.integer_literal(value)])
    if stmt.kind == "op":
        op = operations[stmt.specifier]
        if (
            [arg.width for arg in args] != op.inputs
            or [out.width for out in results] != op.outputs
        ):
            raise ValueError(f"{snippet_name}: invalid types for {op.name}")
        name = op.semantic_func or op.name
        expression = f"{name}({', '.join(str(cpp_value(arg)) for arg in args)})"
        if results:
            return initialize_outputs(results, [expression])
        return cpp.Statement(f"{expression};")
    raise ValueError(
        f"{snippet_name}: unsupported statement {stmt.kind} {stmt.specifier}"
    )


class _ContextBinding:
    def __init__(self, name: str, struct: cpp.Struct):
        self._name = name
        self._fields = {field.name for field in struct.fields}

    def __getattr__(self, field: str) -> str:
        if field not in self._fields:
            raise AttributeError(field)
        return f"{self._name}.{field}"


def _statement_emitter(usage, values):
    usage = copy(usage)
    usage._values = values
    binding = None
    if usage.struct is not None:
        binding = _ContextBinding(usage.parameter_name, usage.struct)

    handlers = {}
    for base in reversed(type(usage).__mro__):
        for method in vars(base).values():
            key = getattr(method, "_statement_key", None)
            if key is not None:
                handlers[key] = method

    def emit_statement(stmt):
        if stmt.specifier is not None:
            exact = handlers.get((stmt.kind, stmt.specifier))
            if exact is not None:
                return exact(usage, binding, stmt)
        general = handlers.get((stmt.kind, None))
        if general is not None:
            return general(usage, binding, stmt, stmt.specifier)
        return None

    return emit_statement

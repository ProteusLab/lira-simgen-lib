from dataclasses import dataclass

from shared.types import OperandType


@dataclass(frozen=True)
class Value:
    name: str
    width: int
    shape: object

    @property
    def cpp_type(self) -> str:
        return OperandType.gen(self.width)

    def __str__(self) -> str:
        return self.name


def _normalized(value, expression):
    width = value.width
    if width == 1 or width < OperandType.bits(width):
        return f"({expression}) & {integer_literal((1 << width) - 1)}"
    return expression


def integer_literal(value: int) -> str:
    if 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        return f"{value}ULL"
    upper, lower = divmod(value, 1 << 64)
    return f"((uint128_t{{{upper}ULL}} << 64) | {lower}ULL)"


def initialize_outputs(outputs, expressions) -> str:
    declarations = []
    if len(outputs) > 1 and len(expressions) == 1:
        names = [f"result_{out}" for out in outputs]
        declarations.append(f"auto [{', '.join(names)}] = {expressions[0]};")
        expressions = names
    if not outputs or len(outputs) != len(expressions):
        raise ValueError("Expected one initializer per output or one tuple initializer")
    declarations.extend(
        f"{out.cpp_type} {out} = {_normalized(out, expr)};"
        for out, expr in zip(outputs, expressions)
    )
    return "\n".join(declarations)


@dataclass
class SnippetFunction:
    name: str
    inputs: dict[int, Value]
    outputs: dict[int, Value]
    body: list[str]
    context: object

    def __call__(self, context, args) -> str:
        arguments = [context] if self.context is not None else []
        arguments.extend(args[index] for index in self.inputs)
        return f"{self.name}({', '.join(arguments)})"

    def definition(self, context_type=None) -> str:
        params = []
        if self.context is not None:
            ty = context_type or f"const {self.context.name}&"
            params.append(f"{ty} {self.context.parameter_name}")
        params.extend(
            f"{value.cpp_type} arg{index}" for index, value in self.inputs.items()
        )

        outputs = list(self.outputs.values())
        return_type = "void"
        body = self.body
        if len(outputs) == 1:
            return_type = outputs[0].cpp_type
            body = [*body, f"return {outputs[0]};"]
        elif outputs:
            types = ", ".join(out.cpp_type for out in outputs)
            return_type = f"std::tuple<{types}>"
            body = [*body, "return {" + ", ".join(map(str, outputs)) + "};"]
        lines = "\n".join(f"  {line}" for stmt in body for line in stmt.splitlines())
        return f"{return_type} {self.name}({', '.join(params)}) {{\n{lines}\n}}"


def compile_snippet(snippet, operations, context=None) -> SnippetFunction:
    values = {}
    inputs = {}
    outputs = {}
    body = []
    usage = context.for_snippet(values) if context is not None else None
    for stmt in snippet.seq.stmts:
        if stmt.shape.lanes_base != 1 or stmt.shape.lanes_mult is not None:
            raise ValueError(f"{snippet.name}: unsupported shape for {stmt.kind}")
        args = [values[name] for name in stmt.inputs]
        results = [
            Value(f"value_{name}", width, stmt.shape)
            for name, width in zip(stmt.outputs, stmt.outputs_types, strict=True)
        ]
        for name, value in zip(stmt.outputs, results):
            if name in values:
                raise ValueError(f"{snippet.name}: repeated definition of {name}")
            values[name] = value

        if stmt.kind == "input":
            (value,) = results
            index = int(stmt.specifier)
            if index < 0 or inputs.setdefault(index, value).width != value.width:
                raise ValueError(f"{snippet.name}: invalid input {index}")
            code = initialize_outputs(results, [f"arg{index}"])
        elif stmt.kind == "output":
            (value,) = args
            index = int(stmt.specifier)
            if index < 0 or index in outputs:
                raise ValueError(f"{snippet.name}: invalid output {index}")
            outputs[index] = value
            continue
        else:
            code = usage.emit_statement(stmt) if usage is not None else None
            if code is None:
                code = _emit_scalar(snippet.name, stmt, args, results, operations)
        body.append(code)

    return SnippetFunction(
        snippet.name,
        dict(sorted(inputs.items())),
        dict(sorted(outputs.items())),
        body,
        context,
    )


def _emit_scalar(snippet_name, stmt, args, results, operations):
    if stmt.kind == "const":
        (out,) = results
        value = int(stmt.specifier, 0) % (1 << out.width)
        return initialize_outputs(results, [integer_literal(value)])
    if stmt.kind == "op":
        op = operations[stmt.specifier]
        if (
            [arg.width for arg in args] != op.inputs
            or [out.width for out in results] != op.outputs
        ):
            raise ValueError(f"{snippet_name}: invalid types for {op.name}")
        name = op.semantic_func or op.name
        expression = f"{name}({', '.join(map(str, args))})"
        if results:
            return initialize_outputs(results, [expression])
        return f"{expression};"
    raise ValueError(
        f"{snippet_name}: unsupported statement {stmt.kind} {stmt.specifier}"
    )

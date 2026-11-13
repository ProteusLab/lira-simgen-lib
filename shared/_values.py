"""C++ value lowering used by the snippet compiler and handlers."""

from shared import cpp
from shared.snippet import Value
from shared.types import OperandType


def cpp_value(value: Value) -> cpp.NamedValue:
    ty = OperandType.gen(value.width)
    if value.shape.lanes_mult is not None:
        ty = f"prot::vec::Scalable<{ty}>"
    elif value.shape.lanes_base != 1:
        ty = f"std::array<{ty}, {value.shape.lanes_base}>"
    return cpp.NamedValue(f"value_{value.name}", ty)


def is_vector(shape) -> bool:
    """Whether this shape needs a vector representation in C++."""
    return shape.lanes_base != 1 or shape.lanes_mult is not None


def normalize(width: int, expression: str) -> str:
    if width == 1 or width < OperandType.bits(width):
        return f"({expression}) & {cpp.integer_literal((1 << width) - 1)}"
    return expression


def initialize_outputs(outputs, expressions) -> cpp.Statement:
    declarations = []
    if len(outputs) > 1 and len(expressions) == 1:
        names = [f"result_{cpp_value(out)}" for out in outputs]
        declarations.append(f"auto [{', '.join(names)}] = {expressions[0]};")
        expressions = names
    if not outputs or len(outputs) != len(expressions):
        raise ValueError("Expected one initializer per output or one tuple initializer")

    for out, expression in zip(outputs, expressions):
        if not is_vector(out.shape):
            expression = normalize(out.width, expression)
        declarations.append(f"{cpp_value(out).declaration()} = {expression};")
    return cpp.Statement("\n".join(declarations))

"""C++ storage and lane-wise lowering for snippet values."""

from shared import cpp
from shared._values import is_vector, normalize
from shared.types import OperandType


def declare_output(usage, ctx, name):
    out = usage.resolve_var(name)
    width, shape = usage.value_type(name)
    if shape.lanes_mult is None:
        return f"{out.declaration()}{{}};"
    count = usage.scalable_lane_count(ctx, shape)
    return f"{out.declaration()} = prot::vec::make<{OperandType.gen(width)}>({count});"


def vector_call(usage, ctx, stmt, helper, args):
    (name,) = stmt.outputs
    out = usage.resolve_var(name)
    call_args = ", ".join(map(str, [out, *args]))
    return cpp.Statement(
        f"{declare_output(usage, ctx, name)}\n"
        f"prot::vec::{helper}({call_args});"
    )


def lane_inputs(usage, names):
    inputs = []
    for name in names:
        value = usage.resolve_var(name)
        _, shape = usage.value_type(name)
        inputs.append(
            f"prot::vec::lane({value}, lane)" if is_vector(shape) else str(value)
        )
    return inputs


def lanewise(usage, ctx, stmt, call):
    if not is_vector(stmt.shape):
        expression = call([str(usage.resolve_var(name)) for name in stmt.inputs])
        if stmt.outputs:
            return usage.init_with(stmt, expression)
        return cpp.Statement(f"{expression};")
    declarations = [declare_output(usage, ctx, name) for name in stmt.outputs]
    outputs = [
        f"prot::vec::lane({usage.resolve_var(name)}, lane)" for name in stmt.outputs
    ]
    body = assign(outputs, stmt.outputs_types, call(lane_inputs(usage, stmt.inputs)))
    return cpp.Statement("\n".join([*declarations, loop(usage, ctx, stmt.shape, body)]))


def assign(outputs, widths, expression):
    if not outputs:
        return cpp.Statement(f"{expression};")
    if len(outputs) == 1:
        return cpp.Statement(f"{outputs[0]} = {normalize(widths[0], expression)};")
    lines = [f"const auto result = {expression};"]
    for index, (out, width) in enumerate(zip(outputs, widths, strict=True)):
        lines.append(f"{out} = {normalize(width, f'std::get<{index}>(result)')};")
    return cpp.Statement("\n".join(lines))


def loop(usage, ctx, shape, body):
    count = (
        shape.lanes_base
        if shape.lanes_mult is None
        else usage.scalable_lane_count(ctx, shape)
    )
    return (
        f"for (std::size_t lane = 0, count = {count}; lane < count; ++lane) {{\n"
        f"{body.render(indent=2)}\n}}"
    )

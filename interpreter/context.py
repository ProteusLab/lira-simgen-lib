from collections.abc import Callable

from interpreter.fpu import float_call
from shared import cpp
from shared._values import is_vector, normalize
from shared.context import BaseContext, context, emit
from shared.types import OperandType


@context(name="ExecuteContext")
class ExecuteContext(BaseContext):
    cpu = "CPU&"
    mem = "Memory&"

    def __init__(self, state, operations):
        self.state = state
        self.operations = operations

    @emit("read")
    def read_register(self, ctx, stmt, name):
        index = self.resolve_var(stmt.inputs[0])
        register = self.state.registers[name]
        if not is_vector(stmt.shape):
            return self.init_with(stmt, register.read(index, cpu=ctx.cpu))
        (out,) = self._outputs(stmt)
        width, _ = self.value_type(stmt.outputs[0])
        return cpp.Statement(
            self._declare_vector(ctx, stmt, out, width)
            + "\n"
            + register.read_vector(index, out, width, cpu=ctx.cpu)
        )

    @emit("write")
    def write_register(self, ctx, stmt, name):
        index, value = map(self.resolve_var, stmt.inputs)
        register = self.state.registers[name]
        if not is_vector(stmt.shape):
            return register.write(index, value, cpu=ctx.cpu)
        width, _ = self.value_type(stmt.inputs[1])
        return register.write_vector(index, value, width, cpu=ctx.cpu)

    @emit("env")
    def call_environment(self, ctx, stmt, name):
        function = self.state.environment[name]
        return self._lanewise(ctx, stmt, lambda args: function.call(ctx.cpu, ctx.mem, args))

    @emit("cond_env")
    def call_conditional_environment(self, ctx, stmt, name):
        function = self.state.environment[name]
        num_args = len(stmt.inputs) - len(stmt.outputs)

        def call(args):
            condition, *inputs = args[:num_args]
            expression = function.call(ctx.cpu, ctx.mem, inputs)
            if not stmt.outputs:
                return f"if ({condition}) {expression}"
            if len(stmt.outputs) == 1:
                fallback = args[num_args]
            else:
                values = ", ".join(map(str, args[num_args:]))
                fallback = f"decltype({expression}){{{values}}}"
            return f"{condition} ? {expression} : {fallback}"

        return self._lanewise(ctx, stmt, call)

    @emit("fop")
    def call_float_operation(self, ctx, stmt, name):
        return self._lanewise(ctx, stmt, lambda args: float_call(name, ctx.cpu, args))

    @emit("op")
    def call_operation(self, ctx, stmt, name):
        return self._lanewise(ctx, stmt, lambda args: self._operation(name, args))

    @emit("const")
    def constant(self, ctx, stmt, specifier):
        (width,) = stmt.outputs_types
        literal = cpp.integer_literal(int(specifier, 0) % (1 << width))
        if not is_vector(stmt.shape):
            return self.init_with(stmt, literal)
        return self._vector_call(ctx, stmt, "splat", [literal])

    @emit("index")
    def indices(self, ctx, stmt, specifier):
        return self._vector_call(ctx, stmt, "iota", [])

    @emit("replicate")
    def replicate(self, ctx, stmt, specifier):
        return self._vector_call(ctx, stmt, "splat", map(self.resolve_var, stmt.inputs))

    @emit("gather")
    def gather(self, ctx, stmt, specifier):
        return self._vector_call(ctx, stmt, "gather", map(self.resolve_var, stmt.inputs))

    @emit("extract_first")
    def extract_first(self, ctx, stmt, specifier):
        return self._vector_call(ctx, stmt, "resize", map(self.resolve_var, stmt.inputs))

    @emit("extend_zero")
    def extend_zero(self, ctx, stmt, specifier):
        return self._vector_call(ctx, stmt, "resize", map(self.resolve_var, stmt.inputs))

    @emit("fold")
    def fold(self, ctx, stmt, name):
        outs = self._outputs(stmt)
        states = [self.resolve_var(arg) for arg in stmt.inputs[: len(outs)]]
        vectors = stmt.inputs[len(outs) :]
        call = self._operation(name, [*outs, *self._lane_inputs(vectors)])
        step = self._assign(outs, stmt.outputs_types, call)
        return cpp.Statement(
            self.init_with(stmt, *states).text + "\n" + self._loop(ctx, stmt, step)
        )

    def _operation(self, name, args):
        op = self.operations[name]
        function = op.semantic_func or op.name
        return f"{function}({', '.join(map(str, args))})"

    def _outputs(self, stmt):
        return [self.resolve_var(name) for name in stmt.outputs]

    def _declare_vector(self, ctx, stmt, out, width):
        if stmt.shape.lanes_mult is None:
            return f"{out.declaration()}{{}};"
        count = self.state.lane_count(stmt.shape, ctx.cpu)
        return f"{out.declaration()} = prot::vec::make<{OperandType.gen(width)}>({count});"

    def _vector_call(self, ctx, stmt, helper, args):
        (out,) = self._outputs(stmt)
        (width,) = stmt.outputs_types
        call_args = ", ".join(map(str, [out, *args]))
        return cpp.Statement(
            self._declare_vector(ctx, stmt, out, width)
            + "\n"
            + f"prot::vec::{helper}({call_args});"
        )

    def _lane_inputs(self, names):
        values = [self.resolve_var(name) for name in names]
        return [
            f"prot::vec::lane({value}, lane)"
            if is_vector(self.value_type(name)[1])
            else str(value)
            for name, value in zip(names, values)
        ]

    def _lanewise(self, ctx, stmt, call: Callable):
        if not is_vector(stmt.shape):
            expression = call(list(map(str, map(self.resolve_var, stmt.inputs))))
            return self.init_with(stmt, expression) if stmt.outputs else f"{expression};"
        outs = self._outputs(stmt)
        declarations = [
            self._declare_vector(ctx, stmt, out, width)
            for out, width in zip(outs, stmt.outputs_types)
        ]
        lanes = [f"prot::vec::lane({out}, lane)" for out in outs]
        code = self._assign(lanes, stmt.outputs_types, call(self._lane_inputs(stmt.inputs)))
        return cpp.Statement("\n".join([*declarations, self._loop(ctx, stmt, code)]))

    @staticmethod
    def _assign(outputs, widths, expression):
        if not outputs:
            return cpp.Statement(f"{expression};")
        if len(outputs) == 1:
            return cpp.Statement(f"{outputs[0]} = {normalize(widths[0], expression)};")
        lines = [f"const auto result = {expression};"]
        for i, (out, width) in enumerate(zip(outputs, widths)):
            lines.append(f"{out} = {normalize(width, f'std::get<{i}>(result)')};")
        return cpp.Statement("\n".join(lines))

    def _loop(self, ctx, stmt, body):
        count = self.state.lane_count(stmt.shape, ctx.cpu)
        return (
            f"for (std::size_t lane = 0, count = {count}; lane < count; ++lane) {{\n"
            f"{body.render(indent=2)}\n}}"
        )

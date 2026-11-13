from interpreter.fpu import float_call
from shared import cpp
from shared._values import is_vector
from shared.context import BaseContext, context, emit


@context(name="ExecuteContext")
class ExecuteContext(BaseContext):
    cpu = "CPU&"
    mem = "Memory&"
    # Protea's RV32 multiply-high snippets use a 32-bit count with asr_64.
    validate_operation_widths = False

    def __init__(self, state):
        self.state = state

    def scalable_lane_count(self, ctx, shape):
        return self.state.lane_count(shape, ctx.cpu)

    @emit("read")
    def read_register(self, ctx, stmt, name):
        index = self.resolve_var(stmt.inputs[0])
        register = self.state.registers[name]
        if not is_vector(stmt.shape):
            return self.init_with(stmt, register.read(index, cpu=ctx.cpu))
        (output,) = stmt.outputs
        out = self.resolve_var(output)
        width, _ = self.value_type(output)
        storage = self.declare_output(ctx, output)
        read = register.read_vector(index, out, width, cpu=ctx.cpu)
        return cpp.Statement(f"{storage.text}\n{read}")

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
        return self.lanewise(ctx, stmt, lambda args: function.call(ctx.cpu, ctx.mem, args))

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

        return self.lanewise(ctx, stmt, call)

    @emit("fop")
    def call_float_operation(self, ctx, stmt, name):
        return self.lanewise(ctx, stmt, lambda args: float_call(name, ctx.cpu, args))

# lira-simgen-lib/lib/nodes.py

from typing import List, Optional

from lira.arch import Operation

from lib.operand import Constant, Variable


def render_nodes(nodes) -> str:
    return "\n".join(str(node) for node in nodes)


class Node:
    def cpp_body(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} has no C++ rendering")

    def __str__(self) -> str:
        return self.cpp_body()


class Input(Node):
    def __init__(self, var: Variable, source: str):
        self.var: Variable = var
        self.source: str = source

    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.var} = {self.source};
"""


class ConstDef(Node):
    def __init__(self, const: Constant):
        self.const: Constant = const

    def cpp_body(self) -> str:
        return self.const.definition


class Op(Node):
    def __init__(self, outs: List[Variable], op: Operation, args: List[Variable]):
        self.outs: List[Variable] = outs
        self.op: Operation = op
        self.args: List[Variable] = args

    @property
    def out(self) -> Variable:
        return self.outs[0]

    def cpp_body(self) -> str:
        from lib.cpp.func import Func

        call = Func.from_op(self.op)([a.name for a in self.args])
        defs = "\n".join(o.definition for o in self.outs)
        if len(self.outs) == 1:
            return f"{defs}\n{self.outs[0]} = {call};\n"
        names = ", ".join(o.name for o in self.outs)
        return f"{defs}\nstd::tie({names}) = {call};\n"


class Fop(Node):
    """`fop`: a standard float operation (runtime/lira_fp.hh) on the FPU
    state of the CPU; the flags it raises are accumulated."""

    def __init__(self, outs: List[Variable], fop, args: List[Variable], fpu):
        from lira.float_ops import modifiers_of, parse

        self.outs: List[Variable] = outs
        self.fop = fop
        self.args: List[Variable] = args
        # FPU model of the generator (wraps the call with the FPU state)
        self.fpu = fpu
        _, self.n, self.m = parse(fop)
        # `default_nan`, `no_flags` (LIRA float_ops.MODIFIERS)
        self.modifiers: List[str] = modifiers_of(fop)

    def cpp_body(self) -> str:
        widths = f"{self.n}" if self.m is None else f"{self.n}, {self.m}"
        args = ", ".join(["fpu"] + [a.name for a in self.args])
        call = f"prot::fp::{self.fop.semantic_base}<{widths}>({args})"
        defs = "\n".join(o.definition for o in self.outs)
        if len(self.outs) != 1:
            raise ValueError(f"{self.fop.name}: several outputs are not supported")
        if self.fpu is None:
            raise ValueError(f"{self.fop.name}: the generator has no FPU model")
        return f"{defs}\n{self.fpu.wrap(f'{self.outs[0]} = {call};', self.modifiers)}"


class ReadReg(Node):
    def __init__(self, rf, index: Variable, var: Variable):
        self.rf = rf
        self.index: Variable = index
        self.var: Variable = var

    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.rf.read(self.index, self.var)}
"""


class WriteReg(Node):
    def __init__(self, rf, index: Variable, value: Variable):
        self.rf = rf
        self.index: Variable = index
        self.value: Variable = value

    def cpp_body(self) -> str:
        return self.rf.write(self.index, self.value)


def env_target(outs: List[Variable]) -> Optional[str]:
    """Where the result of an environment call goes: its output, or
    `std::tie(...)` of its outputs (the call returns a tuple)."""
    if not outs:
        return None
    if len(outs) == 1:
        return str(outs[0])
    return f"std::tie({', '.join(o.name for o in outs)})"


class ReadMem(Node):
    """An environment call with outputs."""

    def __init__(self, outs: List[Variable], inputs: List[Variable], interface):
        self.outs: List[Variable] = outs
        self.inputs: List[Variable] = inputs
        self.interface = interface

    def cpp_body(self) -> str:
        defs = "".join(f"{o.definition}\n" for o in self.outs)
        return f"""{defs}{self.interface(self.inputs, env_target(self.outs))}
"""


class EnvExec(Node):
    def __init__(self, inputs: List[Variable], interface):
        self.inputs: List[Variable] = inputs
        self.interface = interface

    def cpp_body(self) -> str:
        return self.interface(self.inputs, None)


class CondEnv(Node):
    """`cond_env`: call the environment function only if `cond` holds,
    otherwise produce the `on_false` values."""

    def __init__(
        self,
        cond: Variable,
        inputs: List[Variable],
        on_false: List[Variable],
        outs: List[Variable],
        interface,
    ):
        self.cond: Variable = cond
        self.inputs: List[Variable] = inputs
        self.on_false: List[Variable] = on_false
        self.outs: List[Variable] = outs
        self.interface = interface

    def cpp_body(self) -> str:
        defs = "".join(f"{o.definition}\n" for o in self.outs)
        call = self.interface(self.inputs, env_target(self.outs))
        if not self.outs:
            return f"{defs}if ({self.cond}) {{\n{call}\n}}\n"
        other = "\n".join(f"{o} = {v};" for o, v in zip(self.outs, self.on_false))
        return f"{defs}if ({self.cond}) {{\n{call}\n}} else {{\n{other}\n}}\n"


LANE_INDEX = "lane_i"


class LaneLoop(Node):
    """A lane-wise statement (`op`, `fop`, `env`, `cond_env` on vectors): the
    scalar node `body` (built on LaneViews) run for every lane, in lane order.
    `count` is the C++ expression of the number of lanes."""

    def __init__(self, outs: List[Variable], count: str, body: Node):
        self.outs: List[Variable] = outs
        self.count: str = count
        self.body: Node = body

    def cpp_body(self) -> str:
        defs = "".join(f"{o.definition}\n" for o in self.outs)
        return f"""{defs}for (std::size_t {LANE_INDEX} = 0, lane_n = {self.count}; {LANE_INDEX} < lane_n; ++{LANE_INDEX}) {{
{self.body.cpp_body()}
}}
"""


class VecCall(Node):
    """`prot::vec::<helper>(out, args...)` (runtime/lira_vec.hh): index,
    replicate, gather, extract_first, extend_zero."""

    def __init__(self, out: Variable, helper: str, args: List[Variable]):
        self.out: Variable = out
        self.helper: str = helper
        self.args: List[Variable] = args

    def cpp_body(self) -> str:
        args = "".join(f", {a.name}" for a in self.args)
        return f"""{self.out.definition}
prot::vec::{self.helper}({self.out}{args});
"""


class ArenaScope(Node):
    """The scalable values of an instruction are released when it ends."""

    def cpp_body(self) -> str:
        return "prot::vec::ArenaScope arena_scope;\n"


class Fold(Node):
    """`fold op states... vectors...`: states = the first outputs of
    op(states..., lanes...) over the lanes (`count`: the C++ expression of
    their number)."""

    def __init__(self, outs: List[Variable], op: Operation, states: List[Variable],
                 vectors: List[Variable], count: str):
        self.outs: List[Variable] = outs
        self.op: Operation = op
        self.states: List[Variable] = states
        self.vectors: List[Variable] = vectors
        self.count: str = count

    def cpp_body(self) -> str:
        from lib.cpp.func import Func

        i = LANE_INDEX
        args = [o.name for o in self.outs] + [f"prot::vec::lane({v.name}, {i})" for v in self.vectors]
        call = Func.from_op(self.op)(args)
        if len(self.op.outputs) == 1:
            step = f"{self.outs[0]} = {call};"
        else:
            step = f"const auto r = {call};\n" + "\n".join(
                f"  {o} = std::get<{k}>(r);" for k, o in enumerate(self.outs))
        defs = "\n".join(o.definition for o in self.outs)
        init = "\n".join(f"{o} = {st};" for o, st in zip(self.outs, self.states))
        return f"""{defs}
{init}
for (std::size_t {i} = 0, lane_n = {self.count}; {i} < lane_n; ++{i}) {{
  {step}
}}
"""


class ReadRegLanes(Node):
    """`read` of a register as lanes of `lane_width` bits (rendered by the
    register-file model)."""

    def __init__(self, rf, index: Variable, var: Variable, lane_width: int):
        self.rf = rf
        self.index: Variable = index
        self.var: Variable = var
        self.lane_width: int = lane_width

    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.rf.read_lanes(self.index, self.var, self.lane_width)}
"""


class WriteRegLanes(Node):
    """`write` of lanes of `lane_width` bits to a register (rendered by the
    register-file model)."""

    def __init__(self, rf, index: Variable, value: Variable, lane_width: int):
        self.rf = rf
        self.index: Variable = index
        self.value: Variable = value
        self.lane_width: int = lane_width

    def cpp_body(self) -> str:
        return self.rf.write_lanes(self.index, self.value, self.lane_width)


class Return(Node):
    def __init__(self, values: List[Variable]):
        self.values: List[Variable] = values

    @property
    def value(self) -> Variable:
        return self.values[0]

    def cpp_body(self) -> str:
        if len(self.values) == 1:
            return f"""return {self.values[0]};"""
        return f"""return {{{", ".join(v.name for v in self.values)}}};"""


class DynConst(Node):
    """Stub: the dyn_const statement is not supported yet."""


class Scan(Node):
    """Stub: the scan statement is not supported yet."""


class Alias(Node):
    """Stub: the alias statement is not supported yet."""

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
        from lira.float_ops import parse

        self.outs: List[Variable] = outs
        self.fop = fop
        self.args: List[Variable] = args
        # FPU model of the generator (wraps the call with the FPU state)
        self.fpu = fpu
        _, self.n, self.m = parse(fop)

    def cpp_body(self) -> str:
        widths = f"{self.n}" if self.m is None else f"{self.n}, {self.m}"
        args = ", ".join(["fpu"] + [a.name for a in self.args])
        call = f"prot::fp::{self.fop.semantic_base}<{widths}>({args})"
        defs = "\n".join(o.definition for o in self.outs)
        if len(self.outs) != 1:
            raise ValueError(f"{self.fop.name}: several outputs are not supported")
        if self.fpu is None:
            raise ValueError(f"{self.fop.name}: the generator has no FPU model")
        return f"{defs}\n{self.fpu.wrap(f'{self.outs[0]} = {call};')}"


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


class ReadMem(Node):
    def __init__(self, var: Variable, inputs: List[Variable], interface):
        self.var: Variable = var
        self.inputs: List[Variable] = inputs
        self.interface = interface

    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.interface(self.inputs, self.var)}
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
        out: Optional[Variable] = self.outs[0] if self.outs else None
        call = self.interface(self.inputs, out)
        if not self.outs:
            return f"{defs}if ({self.cond}) {{\n{call}\n}}\n"
        other = "\n".join(f"{o} = {v};" for o, v in zip(self.outs, self.on_false))
        return f"{defs}if ({self.cond}) {{\n{call}\n}} else {{\n{other}\n}}\n"


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


class Gather(Node):
    """Stub: the gather statement is not supported yet."""


class Fold(Node):
    """Stub: the fold statement is not supported yet."""


class Scan(Node):
    """Stub: the scan statement is not supported yet."""


class Alias(Node):
    """Stub: the alias statement is not supported yet."""

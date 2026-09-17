# lira-simgen-lib/lib/nodes.py

from typing import List

from lira.arch import Operation

from lib.operand import Register, Variable


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


class Op(Node):
    def __init__(self, out: Variable, op: Operation, args: List[Variable]):
        self.out: Variable = out
        self.op: Operation = op
        self.args: List[Variable] = args

    def cpp_body(self) -> str:
        from lib.cpp.func import Func

        return f"""{self.out.definition}
{self.out} = {Func.from_op(self.op)([a.name for a in self.args])};
"""


class ReadReg(Node):
    def __init__(self, reg: Register, var: Variable):
        self.reg: Register = reg
        self.var: Variable = var

    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.reg.read(self.var)}
"""


class WriteReg(Node):
    def __init__(self, reg: Register, value: Variable):
        self.reg: Register = reg
        self.value: Variable = value

    def cpp_body(self) -> str:
        return self.reg.write(self.value)


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


class Return(Node):
    def __init__(self, value: Variable):
        self.value: Variable = value

    def cpp_body(self) -> str:
        return f"""return {self.value};"""


class CondEnv(Node):
    """Stub: the cond_env statement is not supported yet."""


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

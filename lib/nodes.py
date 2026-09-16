# lira-simgen-lib/lib/nodes.py

from typing import List

from lira.arch import Operation

from lib.operand import Operand, Register, Variable


def render_nodes(nodes) -> str:
    return "\n".join(str(node) for node in nodes)


class Node:
    def cpp_body(self) -> str:
        raise NotImplementedError("no rendering backend attached; import lib.cpp.nodes")

    def __str__(self) -> str:
        return self.cpp_body()


class InputAssign(Node):
    def __init__(self, var: Variable, source: str):
        self.var: Variable = var
        self.source: str = source


class OpAssign(Node):
    def __init__(self, out: Variable, op: Operation, args: List[Variable]):
        self.out: Variable = out
        self.op: Operation = op
        self.args: List[Variable] = args


class ReadReg(Node):
    def __init__(self, reg: Register, var: Variable):
        self.reg: Register = reg
        self.var: Variable = var


class WriteReg(Node):
    def __init__(self, reg: Register, value: Variable):
        self.reg: Register = reg
        self.value: Variable = value


class ReadMem(Node):
    def __init__(self, var: Variable, inputs: List[Variable], interface):
        self.var: Variable = var
        self.inputs: List[Variable] = inputs
        self.interface = interface


class EnvExec(Node):
    def __init__(self, inputs: List[Variable], interface):
        self.inputs: List[Variable] = inputs
        self.interface = interface


class MemberAssign(Node):
    def __init__(self, operand: Operand, value: Variable):
        self.operand: Operand = operand
        self.value: Variable = value


class Return(Node):
    def __init__(self, value: Variable):
        self.value: Variable = value


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

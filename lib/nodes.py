# lira-simgen-lib/lib/nodes.py
# Data-flow nodes produced by the semantic builder

from typing import Callable, Dict, List

from lira.arch import Operation

from lib.operand import Register, Variable
from lib.interface import Interface


class NodeImpl:
    """Maps node data classes to the active backend renderer."""

    _impl: Dict[type, Callable] = {}

    @classmethod
    def serves(cls, base):
        def decorator(fn):
            cls._impl[base] = fn
            return fn

        return decorator


def render_nodes(nodes: List) -> str:
    out = []
    for node in nodes:
        fn = NodeImpl._impl.get(type(node))
        if fn is None:
            raise NotImplementedError(
                f"{type(node).__name__} has no backend rendering registered"
            )
        out.append(fn(node))
    return "\n".join(out)


class Input:
    def __init__(self, var: Variable, source: str):
        self.var: Variable = var
        self.source: str = source


class Op:
    def __init__(self, out: Variable, op: Operation, args: List[Variable]):
        self.out: Variable = out
        self.op: Operation = op
        self.args: List[Variable] = args


class ReadReg:
    def __init__(self, reg: Register, var: Variable):
        self.reg: Register = reg
        self.var: Variable = var


class WriteReg:
    def __init__(self, reg: Register, value: Variable):
        self.reg: Register = reg
        self.value: Variable = value


class ReadMem:
    def __init__(self, var: Variable, inputs: List[Variable], interface: Interface):
        self.var: Variable = var
        self.inputs: List[Variable] = inputs
        self.interface: Interface = interface


class EnvExec:
    def __init__(self, inputs: List[Variable], interface: Interface):
        self.inputs: List[Variable] = inputs
        self.interface: Interface = interface


class Return:
    def __init__(self, value: Variable):
        self.value: Variable = value

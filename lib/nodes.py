# lira-simgen-lib/lib/nodes.py
# Data-flow nodes produced by the semantic builder

from typing import Callable, Dict, List, Optional

from lira.arch import Operation

from lib.operand import Register, Variable
from lib.interface import Interface


class NodeImpl:
    _impl: Dict[type, Callable] = {}

    @classmethod
    def serves(cls, base):
        def decorator(fn):
            cls._impl[base] = fn
            return fn

        return decorator

    @classmethod
    def render(cls, node) -> str:
        fn = cls._impl.get(type(node))
        if fn is None:
            raise NotImplementedError(
                f"{type(node).__name__} has no backend rendering registered"
            )
        return fn(node)


class Raw:
    def __init__(self, stmt):
        self.stmt = stmt
        self.shape = stmt.shape


def render_nodes(nodes: List, ctx=None) -> str:
    out = []
    for node in nodes:
        key = getattr(node, "_stmt_key", None)
        handler = ctx.handler(key) if ctx is not None and key is not None else None
        if handler is not None:
            out.append(handler(ctx, node))
            continue
        out.append(NodeImpl.render(node))
    return "\n".join(p for p in out if p)


class Input:
    def __init__(self, var: Variable, source: Variable):
        self.var: Variable = var
        self.source: Variable = source


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


class EnvCall:
    def __init__(
        self,
        inputs: List[Variable],
        interface: Interface,
        out: Optional[Variable] = None,
    ):
        self.inputs: List[Variable] = inputs
        self.interface: Interface = interface
        self.out: Optional[Variable] = out


class Output:
    def __init__(self, value: Variable):
        self.value: Variable = value


class DynConst:
    def __init__(self, out: Variable, shape, name: str):
        self.out: Variable = out
        self.shape = shape
        self.name: str = name

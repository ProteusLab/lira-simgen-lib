# lira-simgen-lib/cpp/nodes.py

from lib.nodes import (
    DynConst,
    EnvCall,
    Input,
    NodeImpl,
    Op,
    ReadReg,
    Output,
    WriteReg,
)
from lib.operand import Constant, Register, Variable

from cpp.context import BaseContext
from cpp.types import OperandType


def _cpp_type(var: Variable) -> str:
    return OperandType.gen(var.width)


def decl(var: Variable) -> str:
    return f"{_cpp_type(var)} {var.name}{{0}};"


@NodeImpl.serves(Constant)
def _constant(node: Constant) -> str:
    return f"{_cpp_type(node)} {node.name} = {node.value};"


@NodeImpl.serves(DynConst)
def _dyn_const(node: DynConst) -> str:
    return f"""{decl(node.out)}
{node.out} = {BaseContext.parameter_name}.{node.name};
"""


@NodeImpl.serves(Input)
def _input(node: Input) -> str:
    if isinstance(node.source, Register):
        return ""
    return f"""{decl(node.var)}
{node.var} = {node.source};
"""


@NodeImpl.serves(Op)
def _op(node: Op) -> str:
    from cpp.func import Func

    return f"""{decl(node.out)}
{node.out} = {Func.from_op(node.op)(*node.args)};
"""


@NodeImpl.serves(ReadReg)
def _read_reg(node: ReadReg) -> str:
    return f"""{decl(node.var)}
{node.reg.rf.read(node.reg, node.var)}
"""


@NodeImpl.serves(WriteReg)
def _write_reg(node: WriteReg) -> str:
    return node.reg.rf.write(node.reg, node.value)


@NodeImpl.serves(EnvCall)
def _env_call(node: EnvCall) -> str:
    if node.out is None:
        return node.interface(node.inputs, None)
    return f"""{decl(node.out)}
{node.interface(node.inputs, node.out)}
"""


@NodeImpl.serves(Output)
def _output(node: Output) -> str:
    return f"return {node.value};"

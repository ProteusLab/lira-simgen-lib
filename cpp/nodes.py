# lira-simgen-lib/cpp/nodes.py

from lib.nodes import EnvExec, Input, NodeImpl, Op, ReadMem, ReadReg, Return, WriteReg
from lib.operand import Constant, Variable

from cpp.types import OperandType


def _cpp_type(var: Variable) -> str:
    return OperandType.gen(var.width)


def _decl(var: Variable) -> str:
    return f"{_cpp_type(var)} {var.name}{{0}};"


@NodeImpl.serves(Constant)
def _constant(node: Constant) -> str:
    return f"{_cpp_type(node)} {node.name} = {node.value};"


@NodeImpl.serves(Input)
def _input(node: Input) -> str:
    return f"""{_decl(node.var)}
{node.var} = {node.source};
"""


@NodeImpl.serves(Op)
def _op(node: Op) -> str:
    from cpp.func import Func

    return f"""{_decl(node.out)}
{node.out} = {Func.from_op(node.op)([a.name for a in node.args])};
"""


@NodeImpl.serves(ReadReg)
def _read_reg(node: ReadReg) -> str:
    return f"""{_decl(node.var)}
{node.reg.rf.read(node.reg, node.var)}
"""


@NodeImpl.serves(WriteReg)
def _write_reg(node: WriteReg) -> str:
    return node.reg.rf.write(node.reg, node.value)


@NodeImpl.serves(ReadMem)
def _read_mem(node: ReadMem) -> str:
    return f"""{_decl(node.var)}
{node.interface(node.inputs, node.var)}
"""


@NodeImpl.serves(EnvExec)
def _env_exec(node: EnvExec) -> str:
    return node.interface(node.inputs, None)


@NodeImpl.serves(Return)
def _return(node: Return) -> str:
    return f"return {node.value};"

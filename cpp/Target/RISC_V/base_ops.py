# lira-simgen-lib/cpp/Target/RISC_V/base_ops.py

from lira.ir_ops import Asr, DivS, Lsl, Lsr, RemS

from cpp.types import OperandType


def _mask(op) -> int:
    return OperandType.bits(op.inputs[0]) - 1


def _asr(op) -> str:
    t = OperandType.gen(op.inputs[0])
    ts = OperandType.gen(op.inputs[0], signed=True)
    return f"""\
arg1 &= {_mask(op)};
return ({t})(({ts})arg0 >> arg1);
"""


def _div_s(op) -> str:
    bits = OperandType.bits(op.inputs[0])
    t = OperandType.gen(op.inputs[0])
    ts = OperandType.gen(op.inputs[0], signed=True)
    return f"""\
if (arg1 == 0) return arg2;
if (({t})arg0 == ({t})1 << {bits - 1} && ({ts})arg1 == -1) return arg0;
return ({t})(({ts})arg0 / ({ts})arg1);
"""


def _rem_s(op) -> str:
    bits = OperandType.bits(op.inputs[0])
    t = OperandType.gen(op.inputs[0])
    ts = OperandType.gen(op.inputs[0], signed=True)
    return f"""\
if (arg1 == 0) return arg0;
if (({t})arg0 == ({t})1 << {bits - 1} && ({ts})arg1 == -1) return 0;
{ts} res = ({ts})arg0 % ({ts})arg1;
return ({t})res;
"""


Lsl._cpp_body = lambda self: f"""\
arg1 &= {_mask(self)};
return arg0 << arg1;
"""
Lsr._cpp_body = lambda self: f"""\
arg1 &= {_mask(self)};
return arg0 >> arg1;
"""

Asr._cpp_body = _asr
DivS._cpp_body = _div_s
RemS._cpp_body = _rem_s

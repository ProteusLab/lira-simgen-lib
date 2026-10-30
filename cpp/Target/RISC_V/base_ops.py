# lira-simgen-lib/cpp/Target/RISC_V/base_ops.py

from lira.ir_ops import Asr, DivS, Lsl, Lsr, RemS

from cpp.types import OperandType


def _mask(op) -> int:
    return OperandType.bits(op.inputs[0]) - 1


def _asr(op) -> str:
    t = OperandType.gen(op.inputs[0])
    ts = OperandType.gen(op.inputs[0], signed=True)
    return f"  b &= {_mask(op)};\n  return ({t})(({ts})a >> b);\n"


def _div_s(op) -> str:
    bits = OperandType.bits(op.inputs[0])
    t = OperandType.gen(op.inputs[0])
    ts = OperandType.gen(op.inputs[0], signed=True)
    return (
        "  if (b == 0) return c;\n"
        f"  if (({t})a == ({t})1 << {bits - 1} && ({ts})b == -1) return a;\n"
        f"  return ({t})(({ts})a / ({ts})b);\n"
    )


def _rem_s(op) -> str:
    bits = OperandType.bits(op.inputs[0])
    t = OperandType.gen(op.inputs[0])
    ts = OperandType.gen(op.inputs[0], signed=True)
    return (
        "  if (b == 0) return a;\n"
        f"  if (({t})a == ({t})1 << {bits - 1} && ({ts})b == -1) return 0;\n"
        f"  {ts} res = ({ts})a % ({ts})b;\n"
        f"  return ({t})res;\n"
    )


Lsl._cpp_body = lambda self: f"  b &= {_mask(self)};\n  return a << b;\n"
Lsr._cpp_body = lambda self: f"  b &= {_mask(self)};\n  return a >> b;\n"
Asr._cpp_body = _asr
DivS._cpp_body = _div_s
RemS._cpp_body = _rem_s

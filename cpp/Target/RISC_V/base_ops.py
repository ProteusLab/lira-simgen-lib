# lira-simgen-lib/cpp/Target/RISC_V/base_ops.py

from pathlib import Path

from lira.ir_ops import Asr, DivS, Lsl, Lsr, RemS

from cpp.types import OperandType
from lib.templates import Templates

_templates = Templates(Path(__file__).parent / "templates")


def _mask(op) -> int:
    return OperandType.bits(op.inputs[0]) - 1


def _asr(op) -> str:
    return _templates.render(
        Path("asr.jinja"),
        mask=_mask(op),
        t=OperandType.gen(op.inputs[0]),
        ts=OperandType.gen(op.inputs[0], signed=True),
    )


def _div_s(op) -> str:
    bits = OperandType.bits(op.inputs[0])
    return _templates.render(
        Path("div_s.jinja"),
        bits_m1=bits - 1,
        t=OperandType.gen(op.inputs[0]),
        ts=OperandType.gen(op.inputs[0], signed=True),
    )


def _rem_s(op) -> str:
    bits = OperandType.bits(op.inputs[0])
    return _templates.render(
        Path("rem_s.jinja"),
        bits_m1=bits - 1,
        t=OperandType.gen(op.inputs[0]),
        ts=OperandType.gen(op.inputs[0], signed=True),
    )


Lsl._cpp_body = lambda self: _templates.render(
    Path("shift.jinja"), mask=_mask(self), op="<<"
)
Lsr._cpp_body = lambda self: _templates.render(
    Path("shift.jinja"), mask=_mask(self), op=">>"
)
Asr._cpp_body = _asr
DivS._cpp_body = _div_s
RemS._cpp_body = _rem_s

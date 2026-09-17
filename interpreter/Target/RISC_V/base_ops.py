# lira-simgen-lib/interpreter/Target/RISC_V/base_ops.py

from lira.ir_ops import Asr, Lsl, Lsr

from lib.types import OperandType

from interpreter.Target.RISC_V.templates import render as _render


def _mask(op) -> int:
    return OperandType.bits(op.inputs[0]) - 1


def _asr(op) -> str:
    return _render(
        "asr.jinja",
        mask=_mask(op),
        t=OperandType.gen(op.inputs[0]),
        ts=OperandType.gen(op.inputs[0], signed=True),
    )


Lsl._cpp_body = lambda self: _render("shift.jinja", mask=_mask(self), op="<<")
Lsr._cpp_body = lambda self: _render("shift.jinja", mask=_mask(self), op=">>")
Asr._cpp_body = _asr

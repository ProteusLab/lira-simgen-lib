# lira-simgen-lib/lib/cpp/base_ops.py

from lira.arch import Operation
from lira.ir_ops import (
    Add,
    And,
    Asr,
    BinaryOp,
    Clz,
    CmpOp,
    Ctz,
    DivS,
    DivU,
    Eq,
    ExtendOp,
    ExtendSign,
    ExtendZero,
    ExtractLow,
    ExtractLowOp,
    Lsl,
    Lsr,
    Mul,
    Ne,
    Neg,
    Not,
    Orr,
    Popcnt,
    RemS,
    RemU,
    Reverse,
    Rol,
    Ror,
    Select,
    Sge,
    Sgt,
    Sle,
    Slt,
    Sub,
    TernaryOp,
    Uge,
    Ugt,
    Ule,
    Ult,
    UnaryOp,
    Xor,
)

from lib.cpp.templates import render as _render
from lib.types import OperandType


def _signed(op: Operation) -> str:
    return OperandType.gen(op.inputs[0], signed=True)


def _in_type(op: Operation) -> str:
    return OperandType.gen(op.inputs[0])


def _out_type(op: Operation) -> str:
    return OperandType.gen(op.outputs[0])


def _include(cls: type) -> None:
    cls._cpp_body = None


for _cls in (
    Operation,
    UnaryOp,
    BinaryOp,
    CmpOp,
    TernaryOp,
    ExtendOp,
    ExtractLowOp,
    Select,
):
    _include(_cls)


Not._cpp_body = lambda self: _render("not_op.jinja")
Neg._cpp_body = lambda self: _render("neg_op.jinja")
Add._cpp_body = lambda self: _render("binary_op.jinja", token="+")
Sub._cpp_body = lambda self: _render("binary_op.jinja", token="-")
Mul._cpp_body = lambda self: _render("binary_op.jinja", token="*")
And._cpp_body = lambda self: _render("binary_op.jinja", token="&")
Orr._cpp_body = lambda self: _render("binary_op.jinja", token="|")
Xor._cpp_body = lambda self: _render("binary_op.jinja", token="^")

Lsl._cpp_body = lambda self: _render("shift.jinja", op="<<")
Lsr._cpp_body = lambda self: _render("shift.jinja", op=">>")
Asr._cpp_body = lambda self: _render("asr.jinja", t=_in_type(self), ts=_signed(self))
Eq._cpp_body = lambda self: _render("cmp_unsigned.jinja", token="==")
Ne._cpp_body = lambda self: _render("cmp_unsigned.jinja", token="!=")
Slt._cpp_body = lambda self: _render("cmp_signed.jinja", token="<", t=_signed(self))
Sle._cpp_body = lambda self: _render("cmp_signed.jinja", token="<=", t=_signed(self))
Sgt._cpp_body = lambda self: _render("cmp_signed.jinja", token=">", t=_signed(self))
Sge._cpp_body = lambda self: _render("cmp_signed.jinja", token=">=", t=_signed(self))
Ult._cpp_body = lambda self: _render("cmp_unsigned.jinja", token="<")
Ule._cpp_body = lambda self: _render("cmp_unsigned.jinja", token="<=")
Ugt._cpp_body = lambda self: _render("cmp_unsigned.jinja", token=">")
Uge._cpp_body = lambda self: _render("cmp_unsigned.jinja", token=">=")
DivU._cpp_body = lambda self: _render("div_u.jinja")
DivS._cpp_body = lambda self: _render("div_s.jinja", t=_in_type(self), ts=_signed(self))
Ror._cpp_body = lambda self: _render(
    "rotate.jinja", width=self.inputs[0], op=">>", rop="<<"
)
Rol._cpp_body = lambda self: _render(
    "rotate.jinja", width=self.inputs[0], op="<<", rop=">>"
)
RemU._cpp_body = lambda self: _render("rem_u.jinja")
RemS._cpp_body = lambda self: _render("rem_s.jinja", t=_in_type(self), ts=_signed(self))
Select._cpp_body = lambda self: _render("select.jinja")
ExtendSign._cpp_body = lambda self: _render(
    "extend_sign.jinja", iw=self.inputs[0], t=_out_type(self)
)
# Values wider than 128 bits are uint256_t: an extension to them is a
# conversion, an extraction from them takes the low 128-bit half (masked by
# Func when the result is narrower).
def _extend_zero(self) -> str:
    if self.outputs[0] > 128:
        return _render("extend_zero_wide.jinja", t=_out_type(self))
    return _render("extend_zero.jinja", iw=self.inputs[0], t=_out_type(self))


def _extract_low(self) -> str:
    if self.inputs[0] > 128:
        if self.outputs[0] > 128:
            raise ValueError(f"{self.name}: no C++ body for results wider than 128 bits")
        return _render("extract_low_wide.jinja", t=_out_type(self))
    return _render("extract_low.jinja", ow=self.outputs[0], t=_in_type(self))


ExtendZero._cpp_body = _extend_zero
ExtractLow._cpp_body = _extract_low
Popcnt._cpp_body = lambda self: _render("popcnt.jinja", width=self.inputs[0])
Ctz._cpp_body = lambda self: _render("ctz.jinja", width=self.inputs[0])
Clz._cpp_body = lambda self: _render("clz.jinja", width=self.inputs[0])
Reverse._cpp_body = lambda self: _render("reverse.jinja", width=self.inputs[0])


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    from lira.arch_ser_yaml import read_arch

    from lib.cpp.func import Func

    ap = argparse.ArgumentParser(
        description="Generate base_ops.hh/base_ops.cc from LIRA IR"
    )
    ap.add_argument("--ir-path", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    arch = read_arch(args.ir_path)
    tables = {t.name: t for t in arch.tables_int}
    funcs = [Func.from_op(op, tables) for op in arch.operations]

    decls = "\n".join(f.declaration for f in funcs)
    defs = "\n".join(f.definition for f in funcs)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "base_ops.hh").write_text(
        f"""\
// Generated by lira-simgen-lib (lib/cpp/base_ops.py). Do not edit.

#ifndef LIRA_STD_OPS_H
#define LIRA_STD_OPS_H

#include <stdint.h>

#ifdef __SIZEOF_INT128__
typedef unsigned __int128 uint128_t;
typedef __int128 int128_t;
#endif

{decls}
#endif // LIRA_STD_OPS_H
"""
    )
    (args.out_dir / "base_ops.cc").write_text(
        f"""\
// Generated by lira-simgen-lib (lib/cpp/base_ops.py). Do not edit.

#include "base_ops.hh"

{defs}
"""
    )

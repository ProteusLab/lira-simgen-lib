# lira-simgen-lib/cpp/base_ops.py

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

from cpp import render as _render
from cpp.types import OperandType


def render_base_ops(operations) -> tuple:
    from cpp.func import Func

    funcs = [Func.from_op(op) for op in operations]
    decls = "\n".join(f.declaration for f in funcs)
    defs = "\n".join(f.definition for f in funcs)
    hh = _render("base_ops.hh.jinja", decls=decls)
    cc = _render("base_ops.cc.jinja", defs=defs)
    return hh, cc


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
RemU._cpp_body = lambda self: _render("rem_u.jinja")
RemS._cpp_body = lambda self: _render("rem_s.jinja", t=_in_type(self), ts=_signed(self))
Select._cpp_body = lambda self: _render("select.jinja")
ExtendSign._cpp_body = lambda self: _render(
    "extend_sign.jinja", iw=self.inputs[0], t=_out_type(self)
)
ExtendZero._cpp_body = lambda self: _render(
    "extend_zero.jinja", iw=self.inputs[0], t=_out_type(self)
)
ExtractLow._cpp_body = lambda self: _render(
    "extract_low.jinja", ow=self.outputs[0], t=_in_type(self)
)
Popcnt._cpp_body = lambda self: _render("popcnt.jinja", width=self.inputs[0])
Ctz._cpp_body = lambda self: _render("ctz.jinja", width=self.inputs[0])
Clz._cpp_body = lambda self: _render("clz.jinja", width=self.inputs[0])
Reverse._cpp_body = lambda self: _render("reverse.jinja", width=self.inputs[0])


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    from lib.target import import_target_modules
    from lira.arch_ser_yaml import read_arch

    ap = argparse.ArgumentParser(
        description="Generate base_ops.hh/base_ops.cc from LIRA IR"
    )
    ap.add_argument("--ir-path", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument(
        "--arch-target",
        required=True,
        help="""Target architecture: interpreter/Target Python package name""",
    )
    args = ap.parse_args()

    import_target_modules(args.arch_target)

    arch = read_arch(args.ir_path)
    hh, cc = render_base_ops(arch.operations)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "base_ops.hh").write_text(hh)
    (args.out_dir / "base_ops.cc").write_text(cc)

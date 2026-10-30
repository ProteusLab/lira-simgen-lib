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


def _extend_sign(op: Operation) -> str:
    iw = op.inputs[0]
    t = _out_type(op)
    return f"""\
  {t} val = a & ((({t})1 << {iw}) - 1);
  {t} sign = (val >> ({iw} - 1)) & 1;
  if (sign)
    return val | (~((({t})1 << {iw}) - 1));
  else
    return val;
"""


def _extend_zero(op: Operation) -> str:
    iw = op.inputs[0]
    t = _out_type(op)
    return f"  return a & ((({t})1 << {iw}) - 1);\n"


def _extract_low(op: Operation) -> str:
    ow = op.outputs[0]
    t = _in_type(op)
    return f"  return a & ((({t})1 << {ow}) - 1);\n"


def _clz(op: Operation) -> str:
    width = op.inputs[0]
    if width == 128:
        return """\
  if (a == 0) return 128;
  uint64_t hi = (uint64_t)(a >> 64);
  if (hi) return clz_64(hi);
  else return 64 + clz_64((uint64_t)a);
"""
    mask = {8: "0x80", 16: "0x8000", 32: "0x80000000", 64: "0x8000000000000000ULL"}[width]
    return f"""\
  if (a == 0) return {width};
  unsigned n = 0;
  while ((a & {mask}) == 0) {{
    a <<= 1;
    n++;
  }}
  return n;
"""


def _ctz(op: Operation) -> str:
    width = op.inputs[0]
    if width == 128:
        return """\
  if (a == 0) return 128;
  uint64_t lo = (uint64_t)a;
  if (lo) return ctz_64(lo);
  else return 64 + ctz_64((uint64_t)(a >> 64));
"""
    return f"""\
  if (a == 0) return {width};
  unsigned n = 0;
  while ((a & 1) == 0) {{
    a >>= 1;
    n++;
  }}
  return n;
"""


def _popcnt(op: Operation) -> str:
    return {
        8: """\
  unsigned cnt = 0;
  while (a) {
    cnt += a & 1;
    a >>= 1;
  }
  return cnt;
""",
        16: "  return popcnt_8(a & 0xFF) + popcnt_8((a >> 8) & 0xFF);\n",
        32: "  return popcnt_16(a & 0xFFFF) + popcnt_16((a >> 16) & 0xFFFF);\n",
        64: "  return popcnt_32(a & 0xFFFFFFFF) + popcnt_32((a >> 32) & 0xFFFFFFFF);\n",
        128: "  return popcnt_64((uint64_t)a) + popcnt_64((uint64_t)(a >> 64));\n",
    }[op.inputs[0]]


def _reverse(op: Operation) -> str:
    return {
        8: """\
  a = ((a & 0xF0) >> 4) | ((a & 0x0F) << 4);
  a = ((a & 0xCC) >> 2) | ((a & 0x33) << 2);
  a = ((a & 0xAA) >> 1) | ((a & 0x55) << 1);
  return a;
""",
        16: """\
  a = ((a & 0xFF00) >> 8) | ((a & 0x00FF) << 8);
  a = ((a & 0xF0F0) >> 4) | ((a & 0x0F0F) << 4);
  a = ((a & 0xCCCC) >> 2) | ((a & 0x3333) << 2);
  a = ((a & 0xAAAA) >> 1) | ((a & 0x5555) << 1);
  return a;
""",
        32: """\
  a = ((a & 0xFFFF0000) >> 16) | ((a & 0x0000FFFF) << 16);
  a = ((a & 0xFF00FF00) >> 8) | ((a & 0x00FF00FF) << 8);
  a = ((a & 0xF0F0F0F0) >> 4) | ((a & 0x0F0F0F0F) << 4);
  a = ((a & 0xCCCCCCCC) >> 2) | ((a & 0x33333333) << 2);
  a = ((a & 0xAAAAAAAA) >> 1) | ((a & 0x55555555) << 1);
  return a;
""",
        64: """\
  a = ((a & 0xFFFFFFFF00000000ULL) >> 32) | ((a & 0x00000000FFFFFFFFULL) << 32);
  a = ((a & 0xFFFF0000FFFF0000ULL) >> 16) | ((a & 0x0000FFFF0000FFFFULL) << 16);
  a = ((a & 0xFF00FF00FF00FF00ULL) >> 8) | ((a & 0x00FF00FF00FF00FFULL) << 8);
  a = ((a & 0xF0F0F0F0F0F0F0F0ULL) >> 4) | ((a & 0x0F0F0F0F0F0F0F0FULL) << 4);
  a = ((a & 0xCCCCCCCCCCCCCCCCULL) >> 2) | ((a & 0x3333333333333333ULL) << 2);
  a = ((a & 0xAAAAAAAAAAAAAAAAULL) >> 1) | ((a & 0x5555555555555555ULL) << 1);
  return a;
""",
        128: """\
  uint64_t lo = (uint64_t)a;
  uint64_t hi = (uint64_t)(a >> 64);
  return ((uint128_t)reverse_64(lo) << 64) | reverse_64(hi);
""",
    }[op.inputs[0]]


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


Not._cpp_body = lambda self: "  return ~a;\n"
Neg._cpp_body = lambda self: "  return -a;\n"
Add._cpp_body = lambda self: "  return a + b;\n"
Sub._cpp_body = lambda self: "  return a - b;\n"
Mul._cpp_body = lambda self: "  return a * b;\n"
And._cpp_body = lambda self: "  return a & b;\n"
Orr._cpp_body = lambda self: "  return a | b;\n"
Xor._cpp_body = lambda self: "  return a ^ b;\n"

Lsl._cpp_body = lambda self: "  return a << b;\n"
Lsr._cpp_body = lambda self: "  return a >> b;\n"
Asr._cpp_body = lambda self: f"  return ({_in_type(self)})(({_signed(self)})a >> b);\n"
Eq._cpp_body = lambda self: "  return (a == b) ? 1 : 0;\n"
Ne._cpp_body = lambda self: "  return (a != b) ? 1 : 0;\n"
Slt._cpp_body = lambda self: f"  return (({_signed(self)})a < ({_signed(self)})b) ? 1 : 0;\n"
Sle._cpp_body = lambda self: f"  return (({_signed(self)})a <= ({_signed(self)})b) ? 1 : 0;\n"
Sgt._cpp_body = lambda self: f"  return (({_signed(self)})a > ({_signed(self)})b) ? 1 : 0;\n"
Sge._cpp_body = lambda self: f"  return (({_signed(self)})a >= ({_signed(self)})b) ? 1 : 0;\n"
Ult._cpp_body = lambda self: "  return (a < b) ? 1 : 0;\n"
Ule._cpp_body = lambda self: "  return (a <= b) ? 1 : 0;\n"
Ugt._cpp_body = lambda self: "  return (a > b) ? 1 : 0;\n"
Uge._cpp_body = lambda self: "  return (a >= b) ? 1 : 0;\n"
DivU._cpp_body = lambda self: "  return (b == 0) ? c : a / b;\n"
DivS._cpp_body = lambda self: f"  return (b == 0) ? c : ({_in_type(self)})(({_signed(self)})a / ({_signed(self)})b);\n"
RemU._cpp_body = lambda self: "  if (b == 0) return a;\n  return a % b;\n"
RemS._cpp_body = lambda self: f"""\
  if (b == 0) return a;
  {_signed(self)} res = ({_signed(self)})a % ({_signed(self)})b;
  return ({_in_type(self)})res;
"""
Select._cpp_body = lambda self: "  return a ? b : c;\n"
ExtendSign._cpp_body = _extend_sign
ExtendZero._cpp_body = _extend_zero
ExtractLow._cpp_body = _extract_low
Popcnt._cpp_body = _popcnt
Ctz._cpp_body = _ctz
Clz._cpp_body = _clz
Reverse._cpp_body = _reverse


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

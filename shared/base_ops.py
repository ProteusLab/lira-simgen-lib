import argparse
from pathlib import Path

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

from shared.cpp import integer_literal
from shared.templates import render
from shared.types import OperandType


def render_base_ops(operations) -> tuple[str, str]:
    declarations = []
    definitions = []
    for op in operations:
        body = getattr(type(op), "_cpp_body", None)
        if body is None:
            raise ValueError(f"No C++ body defined for operation {op.name}")
        params = ", ".join(
            f"{OperandType.gen(width)} arg{i}" for i, width in enumerate(op.inputs)
        )
        name = op.semantic_func or op.name
        signature = f"{OperandType.gen(op.outputs[0])} {name}({params})"
        declarations.append(f"{signature};")
        definitions.append(f"{signature}\n{{\n{body(op)}\n}}\n")
    directory = Path(__file__).with_name("templates")
    return (
        render(directory, "base_ops.hh.jinja", decls="\n".join(declarations)),
        render(directory, "base_ops.cc.jinja", defs="\n".join(definitions)),
    )


def _signed(op: Operation) -> str:
    return OperandType.gen(op.inputs[0], signed=True)


def _in_type(op: Operation) -> str:
    return OperandType.gen(op.inputs[0])


def _out_type(op: Operation) -> str:
    return OperandType.gen(op.outputs[0])


def _extend_sign(op: Operation) -> str:
    iw = op.inputs[0]
    t = _out_type(op)
    return f"""
{t} val = arg0 & ((({t})1 << {iw}) - 1);
{t} sign = (val >> ({iw} - 1)) & 1;
if (sign)
    return val | (~((({t})1 << {iw}) - 1));
else
    return val;
"""


def _extend_zero(op: Operation) -> str:
    iw = op.inputs[0]
    t = _out_type(op)
    return f"return arg0 & ((({t})1 << {iw}) - 1);\n"


def _extract_low(op: Operation) -> str:
    mask = integer_literal((1 << op.outputs[0]) - 1)
    return f"return arg0 & {mask};\n"


def _shift(op: Operation, operator: str) -> str:
    width = op.inputs[0]
    if isinstance(op, Asr):
        value = _signed_value(op, "arg0")
        return (
            f"return arg1 >= {width} ? ({value} < 0 ? -1 : 0) : "
            f"({value} >> arg1);\n"
        )
    return f"return arg1 >= {width} ? 0 : arg0 {operator} arg1;\n"


def _signed_value(op: Operation, arg: str) -> str:
    width = op.inputs[0]
    signed = _signed(op)
    if width == OperandType.bits(width) and width != 1:
        return f"static_cast<{signed}>({arg})"
    sign = integer_literal(1 << (width - 1))
    signed = "int" if width == 1 else signed
    return f"(static_cast<{signed}>({arg} ^ {sign}) - static_cast<{signed}>({sign}))"


def _clz(op: Operation) -> str:
    width = op.inputs[0]
    if width == 128:
        return """
if (arg0 == 0) return 128;
uint64_t hi = (uint64_t)(arg0 >> 64);
if (hi) return clz_64(hi);
else return 64 + clz_64((uint64_t)arg0);
"""
    mask = {8: "0x80", 16: "0x8000", 32: "0x80000000", 64: "0x8000000000000000ULL"}[
        width
    ]
    return f"""
if (arg0 == 0) return {width};
unsigned n = 0;
while ((arg0 & {mask}) == 0) {{
  arg0 <<= 1;
  n++;
}}
return n;
"""


def _ctz(op: Operation) -> str:
    width = op.inputs[0]
    if width == 128:
        return """
if (arg0 == 0) return 128;
uint64_t lo = (uint64_t)arg0;
if (lo) return ctz_64(lo);
else return 64 + ctz_64((uint64_t)(arg0 >> 64));
"""
    return f"""
if (arg0 == 0) return {width};
unsigned n = 0;
while ((arg0 & 1) == 0) {{
    arg0 >>= 1;
    n++;
}}
return n;
"""


def _popcnt(op: Operation) -> str:
    return {
        8: """
unsigned cnt = 0;
while (arg0) {
    cnt += arg0 & 1;
    arg0 >>= 1;
}
return cnt;
""",
        16: "return popcnt_8(arg0 & 0xFF) + popcnt_8((arg0 >> 8) & 0xFF);\n",
        32: "return popcnt_16(arg0 & 0xFFFF) + popcnt_16((arg0 >> 16) & 0xFFFF);\n",
        64: "return popcnt_32(arg0 & 0xFFFFFFFF) + popcnt_32((arg0 >> 32) & 0xFFFFFFFF);\n",
        128: "return popcnt_64((uint64_t)arg0) + popcnt_64((uint64_t)(arg0 >> 64));\n",
    }[op.inputs[0]]


def _reverse(op: Operation) -> str:
    return {
        8: """
arg0 = ((arg0 & 0xF0) >> 4) | ((arg0 & 0x0F) << 4);
arg0 = ((arg0 & 0xCC) >> 2) | ((arg0 & 0x33) << 2);
arg0 = ((arg0 & 0xAA) >> 1) | ((arg0 & 0x55) << 1);
return arg0;
""",
        16: """
arg0 = ((arg0 & 0xFF00) >> 8) | ((arg0 & 0x00FF) << 8);
arg0 = ((arg0 & 0xF0F0) >> 4) | ((arg0 & 0x0F0F) << 4);
arg0 = ((arg0 & 0xCCCC) >> 2) | ((arg0 & 0x3333) << 2);
arg0 = ((arg0 & 0xAAAA) >> 1) | ((arg0 & 0x5555) << 1);
return arg0;
""",
        32: """
arg0 = ((arg0 & 0xFFFF0000) >> 16) | ((arg0 & 0x0000FFFF) << 16);
arg0 = ((arg0 & 0xFF00FF00) >> 8) | ((arg0 & 0x00FF00FF) << 8);
arg0 = ((arg0 & 0xF0F0F0F0) >> 4) | ((arg0 & 0x0F0F0F0F) << 4);
arg0 = ((arg0 & 0xCCCCCCCC) >> 2) | ((arg0 & 0x33333333) << 2);
arg0 = ((arg0 & 0xAAAAAAAA) >> 1) | ((arg0 & 0x55555555) << 1);
return arg0;
""",
        64: """
arg0 = ((arg0 & 0xFFFFFFFF00000000ULL) >> 32) | ((arg0 & 0x00000000FFFFFFFFULL) << 32);
arg0 = ((arg0 & 0xFFFF0000FFFF0000ULL) >> 16) | ((arg0 & 0x0000FFFF0000FFFFULL) << 16);
arg0 = ((arg0 & 0xFF00FF00FF00FF00ULL) >> 8) | ((arg0 & 0x00FF00FF00FF00FFULL) << 8);
arg0 = ((arg0 & 0xF0F0F0F0F0F0F0F0ULL) >> 4) | ((arg0 & 0x0F0F0F0F0F0F0F0FULL) << 4);
arg0 = ((arg0 & 0xCCCCCCCCCCCCCCCCULL) >> 2) | ((arg0 & 0x3333333333333333ULL) << 2);
arg0 = ((arg0 & 0xAAAAAAAAAAAAAAAAULL) >> 1) | ((arg0 & 0x5555555555555555ULL) << 1);
return arg0;
""",
        128: """
uint64_t lo = (uint64_t)arg0;
uint64_t hi = (uint64_t)(arg0 >> 64);
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


Not._cpp_body = lambda self: (
    "return !arg0;\n" if self.inputs[0] == 1 else "return ~arg0;\n"
)
Neg._cpp_body = lambda self: "return -arg0;\n"
Add._cpp_body = lambda self: (
    "return arg0 != arg1;\n" if self.inputs[0] == 1 else "return arg0 + arg1;\n"
)
Sub._cpp_body = lambda self: (
    "return arg0 != arg1;\n" if self.inputs[0] == 1 else "return arg0 - arg1;\n"
)
Mul._cpp_body = lambda self: "return static_cast<decltype(+arg0 + 0U)>(arg0) * arg1;\n"
And._cpp_body = lambda self: "return arg0 & arg1;\n"
Orr._cpp_body = lambda self: "return arg0 | arg1;\n"
Xor._cpp_body = lambda self: "return arg0 ^ arg1;\n"

Lsl._cpp_body = lambda self: _shift(self, "<<")
Lsr._cpp_body = lambda self: _shift(self, ">>")
Asr._cpp_body = lambda self: _shift(self, ">>")
Eq._cpp_body = lambda self: "return (arg0 == arg1) ? 1 : 0;\n"
Ne._cpp_body = lambda self: "return (arg0 != arg1) ? 1 : 0;\n"
Slt._cpp_body = (
    lambda self: f"return {_signed_value(self, 'arg0')} < {_signed_value(self, 'arg1')};\n"
)
Sle._cpp_body = (
    lambda self: f"return {_signed_value(self, 'arg0')} <= {_signed_value(self, 'arg1')};\n"
)
Sgt._cpp_body = (
    lambda self: f"return {_signed_value(self, 'arg0')} > {_signed_value(self, 'arg1')};\n"
)
Sge._cpp_body = (
    lambda self: f"return {_signed_value(self, 'arg0')} >= {_signed_value(self, 'arg1')};\n"
)
Ult._cpp_body = lambda self: "return (arg0 < arg1) ? 1 : 0;\n"
Ule._cpp_body = lambda self: "return (arg0 <= arg1) ? 1 : 0;\n"
Ugt._cpp_body = lambda self: "return (arg0 > arg1) ? 1 : 0;\n"
Uge._cpp_body = lambda self: "return (arg0 >= arg1) ? 1 : 0;\n"
DivU._cpp_body = lambda self: "return (arg1 == 0) ? arg2 : arg0 / arg1;\n"

DivS._cpp_body = (
    lambda self: f"return (arg1 == 0) ? arg2 : ({_in_type(self)})(({_signed(self)})arg0 / ({_signed(self)})arg1);\n"
)

RemU._cpp_body = lambda self: "if (arg1 == 0) return arg0;\nreturn arg0 % arg1;\n"

RemS._cpp_body = lambda self: f"""\
if (arg1 == 0) return arg0;
{_signed(self)} res = ({_signed(self)})arg0 % ({_signed(self)})arg1;
return ({_in_type(self)})res;
"""

Select._cpp_body = lambda self: "return arg0 ? arg1 : arg2;\n"
ExtendSign._cpp_body = _extend_sign
ExtendZero._cpp_body = _extend_zero
ExtractLow._cpp_body = _extract_low
Popcnt._cpp_body = _popcnt
Ctz._cpp_body = _ctz
Clz._cpp_body = _clz
Reverse._cpp_body = _reverse


def _shift_mask(op: Operation) -> int:
    return OperandType.bits(op.inputs[0]) - 1


def _risc_v_asr(op: Operation) -> str:
    return f"""\
arg1 &= {_shift_mask(op)};
return ({_in_type(op)})(({_signed(op)})arg0 >> arg1);
"""


def _risc_v_div_s(op: Operation) -> str:
    bits = OperandType.bits(op.inputs[0])
    t = _in_type(op)
    ts = _signed(op)
    return f"""\
if (arg1 == 0) return arg2;
if (({t})arg0 == ({t})1 << {bits - 1} && ({ts})arg1 == -1) return arg0;
return ({t})(({ts})arg0 / ({ts})arg1);
"""


def _risc_v_rem_s(op: Operation) -> str:
    bits = OperandType.bits(op.inputs[0])
    t = _in_type(op)
    ts = _signed(op)
    return f"""\
if (arg1 == 0) return arg0;
if (({t})arg0 == ({t})1 << {bits - 1} && ({ts})arg1 == -1) return 0;
{ts} res = ({ts})arg0 % ({ts})arg1;
return ({t})res;
"""


def _use_risc_v_bodies() -> None:
    Lsl._cpp_body = lambda self: f"""\
arg1 &= {_shift_mask(self)};
return arg0 << arg1;
"""
    Lsr._cpp_body = lambda self: f"""\
arg1 &= {_shift_mask(self)};
return arg0 >> arg1;
"""
    Asr._cpp_body = _risc_v_asr
    DivS._cpp_body = _risc_v_div_s
    RemS._cpp_body = _risc_v_rem_s


def main() -> None:
    from lira.arch_ser_yaml import read_arch

    parser = argparse.ArgumentParser(description="Generate C++ base operations")
    parser.add_argument("--ir-path", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--arch-target", required=True)
    args = parser.parse_args()

    if args.arch_target == "RISC_V":
        _use_risc_v_bodies()

    header, source = render_base_ops(read_arch(args.ir_path).operations)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "base_ops.hh").write_text(header, encoding="utf-8")
    (args.out_dir / "base_ops.cc").write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

# lira-simgen-lib/cpp/tests/test_base_ops.py

from lira.arch import Operation
from lira.ir_ops import (
    Add,
    And,
    Clz,
    Ctz,
    Eq,
    ExtendSign,
    ExtendZero,
    ExtractLow,
    Mul,
    Ne,
    Neg,
    Not,
    Orr,
    Popcnt,
    RemU,
    Reverse,
    Select,
    Slt,
    Sub,
    Uge,
    Ugt,
    Ule,
    Ult,
    UnaryOp,
    Xor,
)

import cpp.base_ops  # noqa: F401  (bodies are registered at import time)

from cpp.base_ops import render_base_ops


def test_base_classes_have_no_body():
    assert Operation._cpp_body is None
    assert UnaryOp._cpp_body is None


def test_unary_ops():
    assert Not(32)._cpp_body() == "return ~arg0;\n"
    assert Neg(32)._cpp_body() == "return -arg0;\n"


def test_binary_ops():
    assert Add(32)._cpp_body() == "return arg0 + arg1;\n"
    assert Sub(32)._cpp_body() == "return arg0 - arg1;\n"
    assert Mul(32)._cpp_body() == "return arg0 * arg1;\n"
    assert And(32)._cpp_body() == "return arg0 & arg1;\n"
    assert Orr(32)._cpp_body() == "return arg0 | arg1;\n"
    assert Xor(32)._cpp_body() == "return arg0 ^ arg1;\n"


def test_cmp_ops():
    assert Eq(32)._cpp_body() == "return (arg0 == arg1) ? 1 : 0;\n"
    assert Ne(32)._cpp_body() == "return (arg0 != arg1) ? 1 : 0;\n"
    assert Slt(32)._cpp_body() == "return ((int32_t)arg0 < (int32_t)arg1) ? 1 : 0;\n"
    assert Ult(32)._cpp_body() == "return (arg0 < arg1) ? 1 : 0;\n"
    assert Ule(32)._cpp_body() == "return (arg0 <= arg1) ? 1 : 0;\n"
    assert Ugt(32)._cpp_body() == "return (arg0 > arg1) ? 1 : 0;\n"
    assert Uge(32)._cpp_body() == "return (arg0 >= arg1) ? 1 : 0;\n"


def test_div_rem_select():
    from lira.ir_ops import DivU

    assert DivU(32)._cpp_body() == "return (arg1 == 0) ? arg2 : arg0 / arg1;\n"
    assert RemU(32)._cpp_body() == "if (arg1 == 0) return arg0;\nreturn arg0 % arg1;\n"
    assert Select(32)._cpp_body() == "return arg0 ? arg1 : arg2;\n"


def test_extend_and_extract():
    body = ExtendSign(1, 32)._cpp_body()
    assert "uint32_t val = arg0 & (((uint32_t)1 << 1) - 1);" in body
    assert "uint32_t sign = (val >> (1 - 1)) & 1;" in body
    assert "return val;" in body
    assert ExtendZero(5, 32)._cpp_body() == "return arg0 & (((uint32_t)1 << 5) - 1);\n"
    assert ExtractLow(32, 5)._cpp_body() == "return arg0 & (((uint32_t)1 << 5) - 1);\n"


def test_clz_ctz():
    assert "if (arg0 == 0) return 32;" in Clz(32)._cpp_body()
    assert "0x80000000" in Clz(32)._cpp_body()
    assert "clz_64" in Clz(128)._cpp_body()
    assert "while ((arg0 & 1) == 0)" in Ctz(32)._cpp_body()
    assert "ctz_64" in Ctz(128)._cpp_body()


def test_popcnt():
    assert (
        Popcnt(32)._cpp_body()
        == "return popcnt_16(arg0 & 0xFFFF) + popcnt_16((arg0 >> 16) & 0xFFFF);\n"
    )
    assert "while (arg0)" in Popcnt(8)._cpp_body()


def test_reverse():
    assert "0xFF00" in Reverse(16)._cpp_body()
    assert "reverse_64" in Reverse(128)._cpp_body()


def test_render_base_ops():
    hh, cc = render_base_ops([Add(32), Sub(32)])
    assert "uint32_t add_32(uint32_t arg0, uint32_t arg1);" in hh
    assert "uint32_t sub_32(uint32_t arg0, uint32_t arg1);" in hh
    assert "uint32_t add_32(uint32_t arg0, uint32_t arg1)" in cc
    assert "return arg0 + arg1;" in cc

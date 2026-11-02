# lira-simgen-lib/cpp/tests/test_func.py

import pytest

from lira.arch import EnvironmentFunction
from lira.ir_ops import Add, AddOverflow
from lira.ir_builder import SnippetBuilder

from cpp.func import Func
from lib.operand import Variable


def test_declaration_definition():
    func = Func(
        "f", "uint32_t", [Variable("a", 32), Variable("b", 32)], "  return a + b;\n"
    )
    assert func.declaration == "uint32_t f(uint32_t a, uint32_t b);"
    assert func.definition == """
uint32_t f(uint32_t a, uint32_t b)
{
  return a + b;

}
"""


def test_call():
    func = Func("f", "void", [], "")
    assert func(["a", "b"]) == "f(a, b)"


def test_from_op():
    func = Func.from_op(Add(32))
    assert func.name == "add_32"
    assert func.ret == "uint32_t"
    assert [p.name for p in func.params] == ["arg0", "arg1"]
    assert func.declaration == "uint32_t add_32(uint32_t arg0, uint32_t arg1);"


def test_from_op_missing_body():
    with pytest.raises(ValueError):
        Func.from_op(AddOverflow(32))


def test_from_env():
    func = Func.from_env(EnvironmentFunction("getPC", ["pc"], [], [32]))
    assert func.name == "getPC"
    assert func.ret == "uint32_t"
    assert func.params == []
    assert func.declaration == "uint32_t getPC();"


def test_from_snippet_general(index):
    func = Func.from_snippet(index.snippet["decode_0"], index)
    assert func.declaration == "uint8_t decode_0(uint32_t arg0);"
    assert "return _t" in func.body


def test_from_encode_snippet_with_names(index):
    func = Func.from_encode_snippet(index.snippet["encode_0"], index, ["rs1", "rd"])
    assert func.declaration == "uint32_t encode_0(uint32_t rs1, uint32_t rd);"


def test_from_encode_snippet_arity_mismatch(index):
    with pytest.raises(ValueError):
        Func.from_encode_snippet(index.snippet["encode_0"], index, ["rs1"])


def test_from_decode_snippet(index):
    func = Func.from_decode_snippet(index.snippet["decode_0"], index)
    assert func.declaration == "uint8_t decode_0(uint32_t arg0);"


def test_from_constraint_snippet(index):
    func = Func.from_constraint_snippet(index.snippet["constraint_0"], index)
    assert func.declaration == "bool constraint_0(uint32_t arg0);"


def test_from_snippet_missing_output(index):
    builder = SnippetBuilder(name="no_out")
    builder.input(0, 32)
    snippet = builder.build()
    with pytest.raises(ValueError):
        Func.from_snippet(snippet, index)


def test_from_snippet_custom_function(index):
    builder = SnippetBuilder(name="concat")
    a = builder.input(0, 32)
    b = builder.input(1, 32)
    c = builder.input(2, 32)
    b8 = builder.lsl(b, builder.const(8, 32))
    c16 = builder.lsl(c, builder.const(16, 32))
    ab = builder.orr(a, b8)
    out = builder.orr(ab, c16)
    builder.output(out, 0)
    snippet = builder.build()

    func = Func.from_snippet(snippet, index)
    assert func.name == "concat"
    assert func.ret == "uint32_t"
    assert func.declaration == (
        "uint32_t concat(uint32_t arg0, uint32_t arg1, uint32_t arg2);"
    )
    assert func.definition == """
uint32_t concat(uint32_t arg0, uint32_t arg1, uint32_t arg2)
{
uint32_t _t1{0};
_t1 = arg0;

uint32_t _t2{0};
_t2 = arg1;

uint32_t _t3{0};
_t3 = arg2;

uint32_t _t4 = 8;
uint32_t _t5{0};
_t5 = lsl_32(_t2, _t4);

uint32_t _t6 = 16;
uint32_t _t7{0};
_t7 = lsl_32(_t3, _t6);

uint32_t _t8{0};
_t8 = orr_32(_t1, _t5);

uint32_t _t9{0};
_t9 = orr_32(_t8, _t7);

return _t9;
}
"""
    assert func(["arg0", "arg1", "arg2"]) == "concat(arg0, arg1, arg2)"

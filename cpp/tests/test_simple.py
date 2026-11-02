# lira-simgen-lib/cpp/tests/test_simple.py
#
# A minimal end-to-end test-demo

from lira.ir_builder import SnippetBuilder

from cpp.func import Func


def _sum3_snippet():
    # NOTE: Create LIRA IR: an arbitrary snippet computing (a + b) + c.
    builder = SnippetBuilder(name="sum3")
    a = builder.input(0, 32)
    b = builder.input(1, 32)
    c = builder.input(2, 32)
    ab = builder.add(a, b)
    result = builder.add(ab, c)
    builder.output(result, 0)
    return builder.build()


def test_simple_snippet_demo(index):
    # NOTE: Generate C++ for the snippet.
    func = Func.from_snippet(_sum3_snippet(), index)

    assert func.declaration == (
        "uint32_t sum3(uint32_t arg0, uint32_t arg1, uint32_t arg2);"
    )
    assert func.definition == """
uint32_t sum3(uint32_t arg0, uint32_t arg1, uint32_t arg2)
{
uint32_t _t1{0};
_t1 = arg0;

uint32_t _t2{0};
_t2 = arg1;

uint32_t _t3{0};
_t3 = arg2;

uint32_t _t4{0};
_t4 = add_32(_t1, _t2);

uint32_t _t5{0};
_t5 = add_32(_t4, _t3);

return _t5;
}
"""


def test_simple_snippet_with_names(index):
    # NOTE: Explicit parameter names.
    func = Func.from_snippet(_sum3_snippet(), index, param_names=["x", "y", "z"])

    assert func.declaration == "uint32_t sum3(uint32_t x, uint32_t y, uint32_t z);"
    assert func.definition == """
uint32_t sum3(uint32_t x, uint32_t y, uint32_t z)
{
uint32_t _t1{0};
_t1 = x;

uint32_t _t2{0};
_t2 = y;

uint32_t _t3{0};
_t3 = z;

uint32_t _t4{0};
_t4 = add_32(_t1, _t2);

uint32_t _t5{0};
_t5 = add_32(_t4, _t3);

return _t5;
}
"""

# lira-simgen-lib/cpp/tests/test_simple.py
#
# A minimal end-to-end test-demo

from lira.ir_builder import SnippetBuilder

from cpp.func import Func


def test_simple_snippet_demo(index):
    # NOTE: Create LIRA IR: an arbitrary snippet computing (a + b) + c.
    builder = SnippetBuilder(name="sum3")
    a = builder.input(0, 32)
    b = builder.input(1, 32)
    c = builder.input(2, 32)
    ab = builder.add(a, b)
    result = builder.add(ab, c)
    builder.output(result, 0)
    snippet = builder.build()

    # NOTE: Generate C++ for the snippet.
    func = Func.from_snippet(snippet, index)

    assert func.declaration == "uint32_t sum3(uint32_t a, uint32_t b, uint32_t c);"
    assert func.definition == """
uint32_t sum3(uint32_t a, uint32_t b, uint32_t c)
{
    uint32_t _t1{0};
_t1 = a;

uint32_t _t2{0};
_t2 = b;

uint32_t _t3{0};
_t3 = c;

uint32_t _t4{0};
_t4 = add_32(_t1, _t2);

uint32_t _t5{0};
_t5 = add_32(_t4, _t3);

return _t5;
}
"""

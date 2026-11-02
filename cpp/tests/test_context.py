# lira-simgen-lib/cpp/tests/test_context.py

from cpp.context import Context
from cpp.types import OperandType
from lib.operand import Variable


def test_declaration():
    ctx = Context(name="EncCtx", fields=[Variable("const_encoding_part", 32)])
    assert ctx.declaration == "struct EncCtx {\nuint32_t const_encoding_part;\n};\n"


def test_m_ctx():
    assert Context.M_CTX == "ctx"


def test_param():
    ctx = Context(name="DecCtx", fields=[Variable("const_mask", 32)])
    assert ctx.param == "const DecCtx& ctx"


def test_union():
    ctx = Context.union(
        [
            None,
            Context(
                name="DecCtx",
                fields=[
                    Variable("const_mask", 32),
                    Variable("const_encoding_part", 32),
                ],
            ),
            Context(name="DecCtx", fields=[Variable("const_encoding_part", 32)]),
        ]
    )
    assert ctx.name == "DecCtx"
    assert [field.name for field in ctx.fields] == [
        "const_mask",
        "const_encoding_part",
    ]


def test_union_empty():
    assert Context.union([None, None]) is None


def test_initializer():
    mask = Variable("const_mask", 32)
    part = Variable("const_encoding_part", 32)
    ctx = Context(name="DecCtx", fields=[mask, part])
    values = {"const_mask": 51, "const_encoding_part": 19}
    assert (
        ctx.initializer(lambda name: values[name])
        == "DecCtx{.const_mask = 51, .const_encoding_part = 19}"
    )

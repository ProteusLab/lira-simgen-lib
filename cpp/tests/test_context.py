# lira-simgen-lib/cpp/tests/test_context.py

import pytest

from cpp.context import Context, serves
from lib.operand import Variable


def test_declaration():
    ctx = Context(
        name="EncCtx",
        dyn_consts={"const_encoding_part": Variable("const_encoding_part", 32)},
    )
    assert ctx.declaration == "struct EncCtx {\nuint32_t const_encoding_part;\n};\n"


def test_m_ctx():
    assert Context.M_CTX == "ctx"


def test_param():
    ctx = Context(name="DecCtx", dyn_consts={"const_mask": Variable("const_mask", 32)})
    assert ctx.param == "const DecCtx& ctx"


def test_initializer():
    ctx = Context(
        name="DecCtx",
        dyn_consts={
            "const_mask": Variable("const_mask", 32),
            "const_encoding_part": Variable("const_encoding_part", 32),
        },
    )
    assert (
        ctx.initializer(const_mask=51, const_encoding_part=19)
        == "DecCtx{.const_mask = 51, .const_encoding_part = 19}"
    )


def test_initializer_unknown():
    ctx = Context(name="DecCtx", dyn_consts={"const_mask": Variable("const_mask", 32)})
    with pytest.raises(ValueError):
        ctx.initializer(const_mask=51, unknown_const=19)


def test_initializer_missing():
    ctx = Context(
        name="DecCtx",
        dyn_consts={
            "const_mask": Variable("const_mask", 32),
            "const_encoding_part": Variable("const_encoding_part", 32),
        },
    )
    with pytest.raises(ValueError):
        ctx.initializer(const_mask=51)


def test_param_explicit():
    ctx = Context(
        name="DecCtx",
        param="dctx",
        dyn_consts={"const_mask": Variable("const_mask", 32)},
    )
    assert ctx.param == "const DecCtx& dctx"


def test_context_getattr():
    ctx = Context(name="DecCtx", dyn_consts={"const_mask": Variable("const_mask", 32)})
    assert ctx.const_mask.name == "const_mask"
    with pytest.raises(AttributeError):
        ctx.unknown


def test_unexpected_field():
    with pytest.raises(TypeError):
        Context._member("not a variable")


def test_field_without_type_or_width():
    ctx = Context(name="BadCtx", dyn_consts={"mystery": Variable("mystery")})
    with pytest.raises(ValueError):
        ctx.declaration


def test_serves():
    ctx = Context(name="m_cpu", _type="CPU")
    marker = type("GetPC", (), {})
    serves(ctx)("getPC", marker)
    assert ctx._bindings["getPC"] is marker


def test_bind_invoke():
    class Family:
        pass

    class GetPC(Family):
        name = "getPC"

        def __call__(self, inputs, out=None):
            return f"{self.name}()"

    ctx = Context(name="m_cpu", _type="CPU")
    ctx.bind([GetPC()], Family)
    assert ctx.getPC([], None) == "m_cpu.getPC()"

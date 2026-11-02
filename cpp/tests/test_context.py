# lira-simgen-lib/cpp/tests/test_context.py

import pytest
from types import SimpleNamespace

from cpp.context import BaseContext, context, emit
from lira.ir_std import StmtKind
from lib.interface import Interface
from lib.operand import Variable


@context(name="DecCtx")
class DecoderContext(BaseContext):
    const_mask = Variable(width=32, name="const_mask")
    const_encoding_part = Variable(width=32, name="const_encoding_part")


class _Fake(Interface):
    def __call__(self, inputs, out=None):
        return ""


_syscall = _Fake(SimpleNamespace(name="sysCall", inputs=[], outputs=[]))


@context(name="ExecCtx")
class _ExecContext(BaseContext):
    syscall = _syscall


def test_fields():
    assert [f.name for f in DecoderContext().fields] == [
        "const_mask",
        "const_encoding_part",
    ]


def test_declaration():
    ctx = DecoderContext()
    assert (
        ctx.declaration
        == "struct DecCtx {\nuint32_t const_mask;\nuint32_t const_encoding_part;\n};\n"
    )


def test_param():
    assert DecoderContext().param == "const DecCtx& ctx"


def test_initializer():
    ctx = DecoderContext()
    assert (
        ctx.initializer(const_mask=51, const_encoding_part=19)
        == "DecCtx{.const_mask = 51, .const_encoding_part = 19}"
    )


def test_initializer_unknown():
    with pytest.raises(ValueError):
        DecoderContext().initializer(const_mask=51, unknown=19)


def test_initializer_missing_omitted():
    assert DecoderContext().initializer(const_mask=51) == "DecCtx{.const_mask = 51}"


def test_interfaces():
    assert list(_ExecContext().interfaces.values()) == [_syscall]


def test_emit():
    @emit(StmtKind.DYN_CONST, "const_mask")
    def handler(self, ctx, stmt):
        return ""

    assert handler._statement_key == (StmtKind.DYN_CONST, "const_mask")


def test_custom_statement_callback(index):
    from lira.arch import Snippet
    from lira.ir_std import Shape, Statement, StatementSeq

    from cpp.func import Func

    stmts = [
        Statement(Shape(1, None), ["_t0"], [32], "input", "0", []),
        Statement(Shape(1, None), ["_t1"], [32], "custom_read", "", []),
        Statement(Shape(1, None), ["_t2"], [32], "op", "add_32", ["_t0", "_t1"]),
        Statement(Shape(1, None), [], [], "output", "", ["_t2"]),
    ]
    snippet = Snippet(name="snippet_custom", seq=StatementSeq(stmts))

    @context(name="TestCtx")
    class CustomContext(BaseContext):
        @emit("custom_read")
        def read_custom(self, node):
            return f"uint32_t {node.stmt.outputs[0]} = 42;"

    func = Func.from_snippet(snippet=snippet, index=index, ctx=CustomContext())
    assert "_t1 = 42;" in func.body
    assert func.ret == "uint32_t"


def test_context_getattr():
    ctx = DecoderContext()
    assert ctx.const_mask == "ctx.const_mask"
    with pytest.raises(AttributeError):
        ctx.unknown


def test_assign():
    from types import SimpleNamespace

    from lira.ir import Shape

    from lib.operand import Variable

    ctx = DecoderContext()
    node = SimpleNamespace(out=Variable("_t1", 32), shape=Shape(32, None))
    assert ctx.assign(node, "ctx.const_mask") == "uint32_t _t1 = ctx.const_mask;"


def test_handler():
    @context(name="HandlerCtx")
    class Ctx(BaseContext):
        @emit(StmtKind.DYN_CONST, "exact")
        def exact(self, node):
            return "exact"

        @emit(StmtKind.DYN_CONST)
        def wide(self, node):
            return "wide"

    ctx = Ctx()
    assert ctx.handler((StmtKind.DYN_CONST, "exact")) == Ctx.exact
    assert ctx.handler((StmtKind.DYN_CONST, "other")) == Ctx.wide
    assert ctx.handler((StmtKind.CONST, "exact")) is None

# lira-simgen-lib/cpp/tests/test_emitter.py

from lira.ir_builder import SnippetBuilder

from cpp.emitter import BaseEmitter


def _snippet_with_dyn_const():
    sb = SnippetBuilder(name="snippet_0")
    raw = sb.input(0, 32)
    part = sb.dyn_const("const_encoding_part", 32)
    word = sb.orr(raw, part)
    sb.output(word, 0)
    return sb.build()


def test_snippet_ctx():
    ctx = BaseEmitter.snippet_ctx(_snippet_with_dyn_const(), "EncCtx")
    assert ctx is not None
    assert ctx.name == "EncCtx"
    assert [field.name for field in ctx.fields] == ["const_encoding_part"]


def test_snippet_ctx_none(index):
    assert BaseEmitter.snippet_ctx(index.snippet["constraint_0"], "EncCtx") is None

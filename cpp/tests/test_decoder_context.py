# lira-simgen-lib/cpp/tests/test_decoder_context.py

import pytest

from lira.ir_builder import SnippetBuilder

pytest.importorskip("decoder.emitter")

from decoder.emitter import DecoderEmitter


def _constraint_snippet(name, const_name, const_width=32):
    builder = SnippetBuilder(name=name)
    mach = builder.input(0, const_width)
    const = builder.dyn_const(const_name, const_width)
    out = builder.orr(mach, const)
    builder.output(out, 0)
    return builder.build()


def test_validate_unknown_dyn_const():
    emitter = DecoderEmitter(None)
    snippet = _constraint_snippet("constraint_0", "unknown_const")
    with pytest.raises(ValueError):
        emitter._validate(snippet)


def test_validate_width_mismatch():
    emitter = DecoderEmitter(None)
    snippet = _constraint_snippet("constraint_0", "const_mask", 64)
    with pytest.raises(ValueError):
        emitter._validate(snippet)

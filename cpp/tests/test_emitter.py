# lira-simgen-lib/cpp/tests/test_emitter.py

from cpp.func import snippet_funcs


def test_snippet_funcs(index):
    funcs = snippet_funcs(index, ["decode_0", "decode_0", "constraint_0"])
    assert list(funcs) == ["decode_0", "constraint_0"]

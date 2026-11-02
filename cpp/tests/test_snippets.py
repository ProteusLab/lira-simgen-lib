# lira-simgen-lib/cpp/tests/test_snippets.py

from cpp.snippets import build_snippet_funcs, render_snippets


def test_build_snippet_funcs(arch, index):
    funcs = build_snippet_funcs(arch, index)
    by_name = {func.name: func for func in funcs}
    assert set(by_name) == {"decode_0", "encode_0", "constraint_0"}
    assert by_name["decode_0"].declaration == "uint8_t decode_0(uint32_t machInst);"
    assert (
        by_name["encode_0"].declaration
        == "uint32_t encode_0(uint32_t arg0, uint32_t arg1);"
    )
    assert (
        by_name["constraint_0"].declaration == "bool constraint_0(uint32_t machInst);"
    )


def test_render_snippets(arch, index):
    funcs = build_snippet_funcs(arch, index)
    hh, cc = render_snippets(funcs)
    assert "uint8_t decode_0(uint32_t machInst);" in hh
    assert "uint32_t encode_0(uint32_t arg0, uint32_t arg1);" in hh
    assert "bool constraint_0(uint32_t machInst);" in hh
    assert "uint32_t encode_0(uint32_t arg0, uint32_t arg1)" in cc
    assert "return _t" in cc

# lira-simgen-lib/cpp/snippets.py

import cpp.base_ops  # noqa: F401  (C++ bodies for LIRA operations)

from cpp.func import Func
from cpp import render as _render
from lib.snippet import SnippetKind


def render_snippets(funcs) -> tuple:
    decls = "\n".join(func.declaration for func in funcs)
    defs = "\n\n".join(func.definition for func in funcs)
    hh = _render("snippets.hh.jinja", decls=decls)
    cc = _render("snippets.cc.jinja", defs=defs)
    return hh, cc


def build_snippet_funcs(arch, index) -> list:
    funcs = {}

    for insn in arch.instructions:
        enc = insn.encoding
        for name in enc.decode:
            funcs.setdefault(
                name, Func.from_snippet(index.snippet[name], index, SnippetKind.DECODE)
            )
        if enc.encode:
            funcs.setdefault(
                enc.encode,
                Func.from_snippet(index.snippet[enc.encode], index, SnippetKind.ENCODE),
            )
        if enc.constraint_decode:
            funcs.setdefault(
                enc.constraint_decode,
                Func.from_snippet(
                    index.snippet[enc.constraint_decode], index, SnippetKind.CONSTRAINT
                ),
            )
        if enc.constraint_encode:
            funcs.setdefault(
                enc.constraint_encode,
                Func.from_snippet(
                    index.snippet[enc.constraint_encode], index, SnippetKind.CONSTRAINT
                ),
            )

    return list(funcs.values())


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    from lib.target import import_target_modules
    from lira.arch_ser_yaml import read_arch
    from lira.arch_utils import build_arch_index

    ap = argparse.ArgumentParser(
        description="Generate snippets.hh/snippets.cc from LIRA IR"
    )
    ap.add_argument("--ir-path", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument(
        "--arch-target",
        required=True,
        help="""Target architecture: interpreter/Target Python package name""",
    )
    args = ap.parse_args()

    import_target_modules(args.arch_target)

    arch = read_arch(args.ir_path)
    index = build_arch_index(arch)
    funcs = build_snippet_funcs(arch, index)

    hh, cc = render_snippets(funcs)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "snippets.hh").write_text(hh)
    (args.out_dir / "snippets.cc").write_text(cc)

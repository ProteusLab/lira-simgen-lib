#!/usr/bin/env python3

# Loads the LIRA IR and emits the C++ instruction encoder sources

import argparse
from pathlib import Path

import cpp.base_ops

from cpp.context import BaseContext, context, emit
from cpp.func import snippet_funcs
from cpp.isa import Isa, IsaEmitter
from lib.driver import Driver
from lib.operand import Variable
from lib.target import import_target_modules
from lib.templates import Templates
from lira.ir_std import StmtKind


@context(name="EncCtx")
class EncoderContext(BaseContext):
    const_encoding_part = Variable(width=32, name="const_encoding_part")

    def initializer(self, encoding) -> str:
        return super().initializer(
            const_encoding_part=encoding.const_encoding_part,
        )

    @emit(StmtKind.DYN_CONST, "const_encoding_part")
    def read_encoding_part(self, node):
        return self.assign(node, self.const_encoding_part)


def main() -> None:
    ap = argparse.ArgumentParser(description="C++ instruction encoder code generator")
    ap.add_argument("--ir-path", required=True, type=Path, help="Path to LIRA IR")
    ap.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Directory for the generated sources",
    )
    ap.add_argument(
        "--arch-target",
        required=True,
        help="Target architecture",
    )
    args = ap.parse_args()

    import_target_modules(args.arch_target)

    driver = Driver(args.ir_path)
    templates = Templates(Path(__file__).parent / "templates")
    ctx = EncoderContext()

    encodes = snippet_funcs(
        driver.index,
        (inst.encode_snippet for inst in driver.insts),
        ctx=ctx,
    )

    encode_calls = {
        inst.name: encodes[inst.encode_snippet](
            ctx.initializer(inst.insn.encoding),
            *(Isa.operand(i) for i in range(len(inst.operand_names))),
        )
        for inst in driver.insts
    }

    artifacts = {
        **IsaEmitter(driver).artifacts(),
        Path("encoder.hh"): templates.render(name=Path("encoder.hh.jinja")),
        Path("encoder.cc"): templates.render(
            name=Path("encoder.cc.jinja"),
            isa=Isa,
            encodes=encodes,
            insts=driver.insts,
            ctx=ctx,
            encode_calls=encode_calls,
        ),
    }

    Driver.write_artifacts(args.out_dir, artifacts)


if __name__ == "__main__":
    main()

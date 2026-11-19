#!/usr/bin/env python3

# Loads the LIRA IR and emits the C++ instruction decoder sources

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

MACH = Variable(name="machInst", width=32)
from lira.ir_std import StmtKind


@context(name="DecCtx")
class DecoderContext(BaseContext):
    const_mask = Variable(width=32, name="const_mask")
    const_encoding_part = Variable(width=32, name="const_encoding_part")

    def initializer(self, encoding) -> str:
        return super().initializer(
            const_mask=encoding.const_mask,
            const_encoding_part=encoding.const_encoding_part,
        )

    @emit(StmtKind.DYN_CONST, "const_mask")
    def read_mask(self, node):
        return self.assign(node, self.const_mask)

    @emit(StmtKind.DYN_CONST, "const_encoding_part")
    def read_encoding_part(self, node):
        return self.assign(node, self.const_encoding_part)


def main() -> None:
    ap = argparse.ArgumentParser(description="C++ instruction decoder code generator")
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
    ctx = DecoderContext()

    decodes = snippet_funcs(
        driver.index,
        (name for inst in driver.insts for name in inst.insn.encoding.decode),
    )
    constraints = snippet_funcs(
        driver.index, (inst.constraint_decode for inst in driver.insts), ctx=ctx
    )

    funcs = {**decodes, **constraints}

    artifacts = {
        **IsaEmitter(driver).artifacts(),
        Path("decoder.hh"): templates.render(name=Path("decoder.hh.jinja")),
        Path("decoder.cc"): templates.render(
            name=Path("decoder.cc.jinja"),
            isa=Isa,
            decodes=decodes,
            constraints=constraints,
            funcs=funcs,
            insts=driver.insts,
            ctx=ctx,
            mach=MACH,
        ),
    }

    Driver.write_artifacts(args.out_dir, artifacts)


if __name__ == "__main__":
    main()

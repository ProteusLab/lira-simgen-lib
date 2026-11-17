#!/usr/bin/env python3

# Loads the LIRA IR and emits the C++ instruction interpreter sources

import argparse
from pathlib import Path

from lib.driver import Driver
from lib.target import import_target_modules

from interpreter.emitter import InterpEmitter

import interpreter.Target.RISC_V


def main() -> None:
    ap = argparse.ArgumentParser(description="C++ interpreter code generator")
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
        help="""Target architecture name""",
    )
    args = ap.parse_args()

    import_target_modules(args.arch_target)
    import interpreter.Target.RISC_V

    driver = Driver(args.ir_path)
    Driver.write_artifacts(args.out_dir, InterpEmitter(driver).artifacts())


if __name__ == "__main__":
    main()

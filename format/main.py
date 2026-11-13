#!/usr/bin/env python3

import argparse
from pathlib import Path

from lib.driver import Driver
from lib.target import import_target_modules

from format.emitter import FormatterEmitter


def main() -> None:
    ap = argparse.ArgumentParser(description="C++ instruction formatter code generator")
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
    Driver.write_artifacts(args.out_dir, FormatterEmitter(driver).artifacts())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

# lira-simgen-lib/interpreter/main.py
# CLI entry point: loads the LIRA IR and emits the C++ interpreter
# sources into the output directory.

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.driver import Driver

from interpreter.config import SimpleInterpConfig

import interpreter.Target.RISC_V.interface
import interpreter.Target.RISC_V.regfile


def main() -> None:
    ap = argparse.ArgumentParser(description="C++ interpreter generator")
    ap.add_argument("--ir-path", required=True, type=Path, help="Path to LIRA IR")
    ap.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Directory for the generated sources",
    )
    args = ap.parse_args()

    cfg = SimpleInterpConfig()
    driver = Driver(args.ir_path, cfg)
    cfg.emit(driver, args.out_dir)


if __name__ == "__main__":
    main()

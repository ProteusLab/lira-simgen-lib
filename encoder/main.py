#!/usr/bin/env python3

# Loads the LIRA IR and emits the C++ instruction encoder sources

import argparse
from pathlib import Path

from lib.driver import Driver
from lib.target import import_target_modules

from encoder.emitter import EncoderEmitter


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
    emitter = EncoderEmitter()

    entries = emitter.collect(driver.index, driver.insts)
    isa_hh = emitter.emit_isa(driver.arch, driver.insts)
    encoder_hh = emitter.emit_encoder_hh(entries)
    encoder_cc = emitter.emit_encoder_cc(entries)

    Driver.write_artifacts(
        args.out_dir,
        {
            Path("isa.hh"): isa_hh,
            Path("encoder.hh"): encoder_hh,
            Path("encoder.cc"): encoder_cc,
        },
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Verifies the generated LIRA IR.

import argparse
from pathlib import Path

from lira.arch_ser_yaml import read_arch


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify the generated LIRA IR")
    ap.add_argument("--ir-path", required=True, type=Path, help="Path to LIRA IR")
    args = ap.parse_args()

    arch = read_arch(args.ir_path)
    assert len(arch.instructions) == 49
    assert len(arch.snippets) == 17
    assert len(arch.operations) == 52
    print(
        f"IR OK: {len(arch.instructions)} instructions, "
        f"{len(arch.snippets)} snippets, {len(arch.operations)} ops"
    )


if __name__ == "__main__":
    main()

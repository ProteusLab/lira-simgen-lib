"""Convert AArch64 ASL XML specifications into LIRA IR."""

import argparse
from pathlib import Path

from utils.asl2lira.gen import build_arch, simgen_subset, write_yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simgen", type=Path)

    args = parser.parse_args()

    arch = build_arch(args.xml)
    write_yaml(arch, args.output)

    if args.simgen:
        write_yaml(simgen_subset(arch), args.simgen)


if __name__ == "__main__":
    main()

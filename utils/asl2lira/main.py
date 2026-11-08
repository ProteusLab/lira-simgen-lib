"""Convert AArch64 ASL XML specifications into LIRA IR."""

import argparse
from pathlib import Path

from utils.asl2lira.gen import build_arch, write_yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    arch = build_arch(args.xml)
    write_yaml(arch, args.output)


if __name__ == "__main__":
    main()

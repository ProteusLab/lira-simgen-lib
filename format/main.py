import argparse
from pathlib import Path

from shared.templates import render


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the formatter scaffold")
    parser.add_argument("--ir-path", type=Path)
    parser.add_argument("--arch-target", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    source = render(
        Path(__file__).parent, "formatter.cc.jinja", arch_target=args.arch_target
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "formatter.cc").write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

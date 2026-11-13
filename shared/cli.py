import argparse
from pathlib import Path


def default_parser(module_file: str) -> argparse.ArgumentParser:
    module_dir = Path(module_file).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--ir-path", required=True, type=Path)
    parser.add_argument("--arch-target", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--template-dir", type=Path, default=module_dir / "templates")
    return parser

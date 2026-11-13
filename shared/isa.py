import re
from pathlib import Path

from lira.arch_ser_yaml import read_arch

from shared.cli import default_parser
from shared.templates import render


def main() -> None:
    args = default_parser(__file__).parse_args()
    instructions = read_arch(args.ir_path).instructions
    num_operands = max(
        (len(instruction.operand_sizes) for instruction in instructions), default=0
    )
    header = render(
        args.template_dir,
        "isa.hh.jinja",
        instructions=instructions,
        opcode_name=opcode_name,
        num_operands=num_operands,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "isa.hh").write_text(header, encoding="utf-8")


def opcode_name(instruction) -> str:
    return "k" + re.sub(r"[^A-Za-z0-9_]", "_", instruction.name).upper()


if __name__ == "__main__":
    main()

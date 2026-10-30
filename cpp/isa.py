# lira-simgen-lib/cpp/isa.py

from typing import List

from lib.instruction import Instruction

from cpp import render


def render_isa(insts: List[Instruction]) -> str:
    num_operands = max((len(inst.regs) for inst in insts), default=0)
    return render("isa.hh.jinja", insts=insts, num_operands=num_operands)

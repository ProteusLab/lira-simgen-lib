# lira-simgen-lib/cpp/isa.py

from typing import List

from lira.arch import Arch

from lib.attributes import PC_ATTRIBUTE
from lib.instruction import Instruction

from cpp import render
from cpp.types import OperandType


def addr_type_of(arch: Arch) -> str:
    """C++ type of the architecture address, derived from the PC register."""
    for rf in arch.register_files:
        for reg in rf.regs:
            if PC_ATTRIBUTE in reg.attributes:
                return OperandType.gen(rf.reg_size.lanes_base)
    raise ValueError("architecture has no register marked with the 'pc' attribute")


def render_isa(insts: List[Instruction], addr_type: str) -> str:
    num_operands = max((len(inst.regs) for inst in insts), default=0)
    return render(
        "isa.hh.jinja", insts=insts, num_operands=num_operands, addr_type=addr_type
    )

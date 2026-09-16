# lira-simgen-lib/simgen/instruction.py

from typing import List

from lib.operand import Register


class Instruction:
    def __init__(
        self,
        inst_id: int,
        name: str,
        constraint_decode: str,
        sem: List[object],
        regs: List[Register],
        num_src: int,
        num_dst: int,
        has_mem: bool,
        lira_insn=None,
    ):
        self.inst_id: int = inst_id
        self.name: str = name
        self.constraint_decode: str = constraint_decode
        self.sem: List[object] = sem
        self.regs: List[Register] = regs
        self.num_src: int = num_src
        self.num_dst: int = num_dst
        self.has_mem: bool = has_mem
        self.lira_insn = lira_insn

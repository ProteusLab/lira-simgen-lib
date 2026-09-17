# lira-simgen-lib/simgen/instruction.py

from typing import List, Optional

from lira.arch import Instruction as LiraInstruction

from lib.operand import Register


class Instruction:
    def __init__(
        self,
        inst_id: int,
        sem: List[object],
        regs: List[Register],
        num_src: int,
        num_dst: int,
        has_mem: bool,
        insn: Optional[LiraInstruction] = None,
    ):
        self.inst_id: int = inst_id
        self.sem: List[object] = sem
        self.regs: List[Register] = regs
        self.num_src: int = num_src
        self.num_dst: int = num_dst
        self.has_mem: bool = has_mem
        self.insn: Optional[LiraInstruction] = insn

    @property
    def name(self) -> str:
        return self.insn.name.upper()

    @property
    def constraint_decode(self) -> str:
        return self.insn.encoding.constraint_decode

    @property
    def ilen(self) -> int:
        return self.insn.encoding.encoded_size // 8

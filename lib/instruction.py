# lira-simgen-lib/lib/instruction.py

from typing import List

from lira.arch import Instruction as LiraInstruction

from lib.operand import Register


class Instruction:
    def __init__(
        self,
        sem: List[object],
        regs: List[Register],
        insn: LiraInstruction,
    ):
        self.sem: List[object] = sem
        self.regs: List[Register] = regs
        self.insn: LiraInstruction = insn

    @property
    def name(self) -> str:
        return self.insn.name.upper()

    @property
    def snake_name(self) -> str:
        return self.insn.name

    @property
    def constraint_decode(self) -> str:
        return self.insn.encoding.constraint_decode

    @property
    def encode_snippet(self) -> str:
        return self.insn.encoding.encode

    @property
    def ilen(self) -> int:
        return self.insn.encoding.encoded_size // 8

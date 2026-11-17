# lira-simgen-lib/lib/instruction.py

from typing import List

from lira.arch import Instruction as LiraInstruction

from lib.operand import Register


class Instruction:
    def __init__(
        self,
        sem: List[object],
        operands: List[Register],
        insn: LiraInstruction,
    ):
        self.sem: List[object] = sem
        self.operands: List[Register] = operands
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
    def operand_names(self) -> List[str]:
        return self.insn.operand_names

    @property
    def operand_sizes(self) -> List[int]:
        return self.insn.operand_sizes

    def const_value(self, name: str) -> int:
        try:
            return getattr(self.insn.encoding, name)
        except AttributeError as exc:
            raise ValueError(
                f"{self.name}: unknown dynamic constant '{name}' "
                "— incomplete LIRA IR"
            ) from exc

    @property
    def const_mask(self) -> int:
        return self.insn.encoding.const_mask

    @property
    def const_encoding_part(self) -> int:
        return self.insn.encoding.const_encoding_part

    @property
    def ilen(self) -> int:
        return self.insn.encoding.encoded_size // 8

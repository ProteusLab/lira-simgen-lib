# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from lib.instruction import Instruction
from lib.snippet import SnippetKind

from cpp.func import Func
from cpp.isa import render_isa


@dataclass
class EncodeEntry:
    inst: Instruction
    func: Optional[Func] = None
    const_part: Optional[int] = None

    @property
    def signature(self) -> str:
        return self.func.param_list if self.func else ""


class EncoderEmitter:
    def __init__(self, config):
        self.cfg = config

    def _collect(self, index, insts: List[Instruction]) -> List[EncodeEntry]:
        entries = []
        for inst in insts:
            if inst.encode_snippet:
                func = Func.from_snippet(
                    index.snippet[inst.encode_snippet],
                    index,
                    SnippetKind.ENCODE,
                    inst.insn.operand_names,
                )
                entries.append(EncodeEntry(inst, func=func))
            elif not inst.insn.operand_names:
                entries.append(
                    EncodeEntry(inst, const_part=inst.insn.encoding.const_encoding_part)
                )
            else:
                raise ValueError(
                    f"{inst.name}: instruction has operands but no encode snippet"
                )
        return entries

    def emit(self, index, insts: List[Instruction]) -> Tuple[str, str, str]:
        entries = self._collect(index, insts)
        isa_hh = render_isa(insts)

        encoder_hh = self.cfg.templates.render(
            Path(f"{self.cfg.encoder_hh}.jinja"), funcs=entries
        )
        encoder_cc = self.cfg.templates.render(
            Path(f"{self.cfg.encoder_cc}.jinja"), funcs=entries
        )
        return isa_hh, encoder_hh, encoder_cc

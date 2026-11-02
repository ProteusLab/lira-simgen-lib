# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from lib.instruction import Instruction

import cpp.base_ops
from cpp.func import Func
from cpp.isa import addr_type_of, render_isa


@dataclass
class EncodeEntry:
    inst: Instruction
    func: Func

    @property
    def signature(self) -> str:
        return self.func.param_list


class EncoderEmitter:
    def __init__(self, config):
        self.cfg = config

    def _collect(self, index, insts: List[Instruction]) -> List[EncodeEntry]:
        entries = []
        for inst in insts:
            if not inst.encode_snippet:
                raise ValueError(f"{inst.name}: instruction has no encode snippet")
            func = Func.from_encode_snippet(
                index.snippet[inst.encode_snippet],
                index,
                inst.insn.operand_names,
            )
            entries.append(EncodeEntry(inst, func=func))
        return entries

    def emit(self, arch, index, insts: List[Instruction]) -> Tuple[str, str, str]:
        entries = self._collect(index, insts)
        isa_hh = render_isa(insts, addr_type_of(arch))

        encoder_hh = self.cfg.templates.render(
            Path(f"{self.cfg.encoder_hh}.jinja"), funcs=entries
        )
        encoder_cc = self.cfg.templates.render(
            Path(f"{self.cfg.encoder_cc}.jinja"), funcs=entries
        )
        return isa_hh, encoder_hh, encoder_cc

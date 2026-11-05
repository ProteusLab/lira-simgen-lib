# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from dataclasses import dataclass
from pathlib import Path
from typing import List

from lib.instruction import Instruction
from lib.templates import Templates

import cpp.base_ops
from cpp.func import Func
from cpp.isa import addr_type_of, render_isa

_templates = Templates(Path(__file__).parent / "templates")


@dataclass
class EncodeEntry:
    inst: Instruction
    func: Func

    @property
    def signature(self) -> str:
        return self.func.param_list


class EncoderEmitter:
    def collect(self, index, insts: List[Instruction]) -> List[EncodeEntry]:
        """Build one entry per instruction from its encode snippet."""
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

    def emit_isa(self, arch, insts: List[Instruction]) -> str:
        return render_isa(insts, addr_type_of(arch))

    def emit_encoder_hh(self, entries: List[EncodeEntry]) -> str:
        return _templates.render(Path("encoder.hh.jinja"), funcs=entries)

    def emit_encoder_cc(self, entries: List[EncodeEntry]) -> str:
        return _templates.render(Path("encoder.cc.jinja"), funcs=entries)

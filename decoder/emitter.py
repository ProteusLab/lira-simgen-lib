# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import List

from lib.instruction import Instruction
from lib.templates import Templates

from cpp.isa import addr_type_of, render_isa

_templates = Templates(Path(__file__).parent / "templates")


class DecoderEmitter:
    def emit_isa(self, arch, insts: List[Instruction]) -> str:
        return render_isa(insts, addr_type_of(arch))

    def emit_decoder_hh(self) -> str:
        return _templates.render(Path("decoder.hh.jinja"))

    def emit_decoder_cc(self, insts: List[Instruction]) -> str:
        return _templates.render(Path("decoder.cc.jinja"), insts=insts)

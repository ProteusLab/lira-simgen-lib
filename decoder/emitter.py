# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import List, Tuple

from lib.instruction import Instruction

from cpp.isa import render_isa


class DecoderEmitter:
    def __init__(self, config):
        self.cfg = config

    def isa(self, insts: List[Instruction]) -> str:
        return render_isa(insts)

    def decoder(self, insts: List[Instruction]) -> Tuple[str, str]:
        dec_hh = self.cfg.templates.render(Path(f"{self.cfg.decoder_hh}.jinja"))
        dec_cc = self.cfg.templates.render(
            Path(f"{self.cfg.decoder_cc}.jinja"), insts=insts
        )
        return dec_hh, dec_cc

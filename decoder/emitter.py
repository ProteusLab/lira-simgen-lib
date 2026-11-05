# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import Dict

from lib.templates import Templates

_templates = Templates(Path(__file__).parent / "templates")


class DecoderEmitter:
    """Renders the C++ instruction decoder sources for one IR."""

    def __init__(self, driver):
        self._driver = driver

    def artifacts(self) -> Dict[Path, str]:
        num_operands = max((len(inst.regs) for inst in self._driver.insts), default=0)

        decoder_hh = _templates.render(
            Path("decoder.hh.jinja"),
            insts=self._driver.insts,
            num_operands=num_operands,
        )
        decoder_cc = _templates.render(
            Path("decoder.cc.jinja"), insts=self._driver.insts
        )
        return {
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

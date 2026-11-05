# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import Dict

from lib.templates import Templates

from cpp.isa import addr_type_of, render_isa

_templates = Templates(Path(__file__).parent / "templates")


class DecoderEmitter:
    """Renders the C++ instruction decoder sources for one IR."""

    def __init__(self, driver):
        self._driver = driver

    def artifacts(self) -> Dict[Path, str]:
        isa_hh = render_isa(self._driver.insts, addr_type_of(self._driver.arch))
        decoder_hh = _templates.render(Path("decoder.hh.jinja"))
        decoder_cc = _templates.render(
            Path("decoder.cc.jinja"), insts=self._driver.insts
        )
        return {
            Path("isa.hh"): isa_hh,
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

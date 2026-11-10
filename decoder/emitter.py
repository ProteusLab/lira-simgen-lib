# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import Dict, List

from lib.templates import Templates

import cpp.base_ops
from cpp.func import Func

_templates = Templates(Path(__file__).parent / "templates")


class DecoderEmitter:
    """Renders the C++ instruction decoder sources for one IR."""

    def __init__(self, driver):
        self._driver = driver

    def _collect(self) -> List[Func]:
        """Build one function per decode/constraint snippet the decoder calls."""
        funcs = {}
        for insn in self._driver.arch.instructions:
            enc = insn.encoding
            for name in enc.decode:
                funcs.setdefault(
                    name,
                    Func.from_snippet(
                        snippet=self._driver.index.snippet[name],
                        index=self._driver.index,
                    ),
                )
            if enc.constraint_decode:
                funcs.setdefault(
                    enc.constraint_decode,
                    Func.from_snippet(
                        snippet=self._driver.index.snippet[enc.constraint_decode],
                        index=self._driver.index,
                    ),
                )
        return list(funcs.values())

    def artifacts(self) -> Dict[Path, str]:
        num_operands = max((len(inst.regs) for inst in self._driver.insts), default=0)
        funcs = self._collect()

        decoder_hh = _templates.render(
            name=Path("decoder.hh.jinja"),
            insts=self._driver.insts,
            num_operands=num_operands,
        )
        decoder_cc = _templates.render(
            name=Path("decoder.cc.jinja"), insts=self._driver.insts, funcs=funcs
        )
        return {
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

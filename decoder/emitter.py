# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import Dict

import cpp.base_ops
from cpp.emitter import BaseEmitter, emit_function_dict
from cpp.func import Func
from cpp.isa import IsaEmitter


class DecoderEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        self._isa = IsaEmitter(driver)
        self._decodes: Dict[str, Func] = {}
        self._constraints: Dict[str, Func] = {}

    def _collect(self) -> None:
        self._decodes = self.snippet_funcs(
            name for inst in self._driver.insts for name in inst.insn.encoding.decode
        )
        self._constraints = self.snippet_funcs(
            inst.constraint_decode for inst in self._driver.insts
        )

    def artifacts(self) -> Dict[Path, str]:
        self._collect()

        decoder_hh = self._templates.render(name=Path("decoder.hh.jinja"))
        decoder_cc = self._templates.render(
            name=Path("decoder.cc.jinja"),
            decodes=self._decodes,
            constraints=self._constraints,
            decode_definitions=emit_function_dict(self._decodes),
            constraint_definitions=emit_function_dict(
                self._constraints, "const DecCtx& ctx"
            ),
            insts=self._driver.insts,
        )

        return {
            **self._isa.artifacts(),
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

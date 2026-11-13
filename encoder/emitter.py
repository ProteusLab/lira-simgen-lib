# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from pathlib import Path
from typing import Dict

import cpp.base_ops
from cpp.context import Context
from cpp.emitter import BaseEmitter, emit_function_dict
from cpp.isa import Isa, IsaEmitter

_CONTEXT_NAME = "EncCtx"


class EncoderEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        self._isa = IsaEmitter(driver)

    def artifacts(self) -> Dict[Path, str]:
        for inst in self._driver.insts:
            if not inst.encode_snippet:
                raise ValueError(f"{inst.name}: instruction has no encode snippet")

        encodes = self.snippet_funcs(inst.encode_snippet for inst in self._driver.insts)
        contexts = {
            name: self.snippet_ctx(self._driver.index.snippet[name], _CONTEXT_NAME)
            for name in encodes
        }

        encoder_hh = self._templates.render(name=Path("encoder.hh.jinja"))
        encoder_cc = self._templates.render(
            name=Path("encoder.cc.jinja"),
            isa=Isa,
            encodes=encodes,
            encode_definitions=emit_function_dict(
                encodes, {name: ctx.param for name, ctx in contexts.items() if ctx}
            ),
            contexts=contexts,
            ctx=Context.union(contexts.values()),
            insts=self._driver.insts,
        )

        return {
            **self._isa.artifacts(),
            Path("encoder.hh"): encoder_hh,
            Path("encoder.cc"): encoder_cc,
        }

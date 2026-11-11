# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from pathlib import Path
from typing import Dict, Optional

import cpp.base_ops
from cpp.context import Context
from cpp.emitter import BaseEmitter
from cpp.func import Func
from cpp.isa import Isa, IsaEmitter

_CONTEXT_NAME = "EncCtx"


class EncoderEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        self._isa = IsaEmitter(driver)
        self._encodes: Dict[str, Func] = {}
        self._encode_ctxs: Dict[str, Optional[Context]] = {}
        self._encode_calls: Dict[str, str] = {}

    def _collect(self) -> None:
        for inst in self._driver.insts:
            name = inst.encode_snippet

            if not name:
                raise ValueError(f"{inst.name}: instruction has no encode snippet")

            if name not in self._encodes:
                snippet = self._driver.index.snippet[name]
                self._encodes[name] = Func.from_snippet(
                    snippet=snippet, index=self._driver.index
                )
                self._encode_ctxs[name] = self.snippet_ctx(snippet, _CONTEXT_NAME)

            args = [Isa.operand(i) for i in range(len(inst.operand_names))]

            ctx = self._encode_ctxs[name]
            if ctx is None:
                self._encode_calls[inst.name] = self._encodes[name](*args)
            else:
                self._encode_calls[inst.name] = self._encodes[name](
                    ctx.initializer(inst.const_value), *args
                )

    def artifacts(self) -> Dict[Path, str]:
        self._collect()

        encoder_hh = self._templates.render(name=Path("encoder.hh.jinja"))
        encoder_cc = self._templates.render(
            name=Path("encoder.cc.jinja"),
            encodes=self._encodes,
            encode_ctxs=self._encode_ctxs,
            ctx=Context.union(self._encode_ctxs.values()),
            insts=self._driver.insts,
            encode_calls=self._encode_calls,
        )

        return {
            **self._isa.artifacts(),
            Path("encoder.hh"): encoder_hh,
            Path("encoder.cc"): encoder_cc,
        }

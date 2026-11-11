# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import Dict, Optional

from lib.operand import Variable

import cpp.base_ops
from cpp.context import Context
from cpp.emitter import BaseEmitter
from cpp.func import Func
from cpp.isa import Isa, IsaEmitter

_CONTEXT_NAME = "DecCtx"
_MACH = Variable("machInst", 32)


class DecoderEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        self._isa = IsaEmitter(driver)
        self._decodes: Dict[str, Func] = {}
        self._constraints: Dict[str, Func] = {}
        self._constraint_ctxs: Dict[str, Optional[Context]] = {}
        self._decode_calls: Dict[str, str] = {}
        self._constraint_calls: Dict[str, str] = {}

    def _collect(self) -> None:
        for inst in self._driver.insts:
            for operand in inst.operands:
                name = operand.snippet.name
                if name not in self._decodes:
                    self._decodes[name] = Func.from_snippet(
                        snippet=self._driver.index.snippet[name],
                        index=self._driver.index,
                    )
                    self._decode_calls[name] = self._decodes[name](_MACH)

            constraint = inst.constraint_decode

            if not constraint:
                raise ValueError(f"{inst.name}: instruction has no constraint snippet")

            if constraint not in self._constraints:
                snippet = self._driver.index.snippet[constraint]
                self._constraints[constraint] = Func.from_snippet(
                    snippet=snippet,
                    index=self._driver.index,
                )
                self._constraint_ctxs[constraint] = self.snippet_ctx(
                    snippet, _CONTEXT_NAME
                )

            ctx = self._constraint_ctxs[constraint]

            if ctx is None:
                self._constraint_calls[inst.name] = self._constraints[constraint](_MACH)
            else:
                self._constraint_calls[inst.name] = self._constraints[constraint](
                    ctx.initializer(inst.const_value), _MACH
                )

    def artifacts(self) -> Dict[Path, str]:
        self._collect()

        decoder_hh = self._templates.render(name=Path("decoder.hh.jinja"))
        decoder_cc = self._templates.render(
            name=Path("decoder.cc.jinja"),
            isa=Isa,
            decodes=self._decodes,
            constraints=self._constraints,
            constraint_ctxs=self._constraint_ctxs,
            ctx=Context.union(self._constraint_ctxs.values()),
            insts=self._driver.insts,
            decode_calls=self._decode_calls,
            constraint_calls=self._constraint_calls,
        )

        return {
            **self._isa.artifacts(),
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

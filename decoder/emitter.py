# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from pathlib import Path
from typing import Dict

from lib.operand import Variable

import cpp.base_ops
from cpp.context import Context
from cpp.emitter import BaseEmitter
from cpp.func import Func
from cpp.isa import Isa, IsaEmitter

_MACH = Variable("machInst", 32)


class DecoderEmitter(BaseEmitter):
    dec_ctx = Context(
        name="DecCtx",
        dyn_consts={
            "const_mask": Variable("const_mask", 32),
            "const_encoding_part": Variable("const_encoding_part", 32),
        },
    )

    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")

        self._isa = IsaEmitter(driver)
        self._decodes: Dict[str, Func] = {}
        self._constraints: Dict[str, Func] = {}
        self._decode_calls: Dict[str, str] = {}
        self._constraint_calls: Dict[str, str] = {}

    def _validate(self, snippet) -> None:
        declared = {field.name: field for field in self.dec_ctx.fields}
        for field in Func.dyn_fields(snippet):
            if field.name not in declared:
                raise ValueError(
                    f"snippet '{snippet.name}': unknown dynamic constant "
                    f"'{field.name}' — incomplete LIRA IR"
                )
            if declared[field.name].width != field.width:
                raise ValueError(
                    f"snippet '{snippet.name}': dynamic constant '{field.name}' "
                    f"has width {field.width}, expected {declared[field.name].width}"
                )

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
                self._validate(snippet)
                self._constraints[constraint] = Func.from_snippet(
                    snippet=snippet,
                    index=self._driver.index,
                )

            self._constraint_calls[inst.name] = self._constraints[constraint](
                self.dec_ctx.initializer(
                    const_mask=inst.const_mask,
                    const_encoding_part=inst.const_encoding_part,
                ),
                _MACH,
            )

    def artifacts(self) -> Dict[Path, str]:
        self._collect()

        decoder_hh = self._templates.render(name=Path("decoder.hh.jinja"))
        decoder_cc = self._templates.render(
            name=Path("decoder.cc.jinja"),
            isa=Isa,
            decodes=self._decodes,
            constraints=self._constraints,
            ctx=self.dec_ctx,
            insts=self._driver.insts,
            decode_calls=self._decode_calls,
            constraint_calls=self._constraint_calls,
        )

        return {
            **self._isa.artifacts(),
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

# lira-simgen-lib/decoder/emitter.py
# Code generation of the instruction decoder.

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.instruction import Instruction
from lib.templates import Templates

import cpp.base_ops
from cpp.context import Context
from cpp.func import Func

_templates = Templates(Path(__file__).parent / "templates")

_CONTEXT_NAME = "DecCtx"


@dataclass
class DecodeEntry:
    inst: Instruction
    call_args: str


class DecoderEmitter:
    """Renders the C++ instruction decoder sources for one IR."""

    def __init__(self, driver):
        self._driver = driver

    @staticmethod
    def _snippet_ctx(snippet) -> Optional[Context]:
        fields = Func.dyn_fields(snippet)
        return Context(name=_CONTEXT_NAME, fields=fields) if fields else None

    @staticmethod
    def _union_ctx(ctxs) -> Optional[Context]:
        name = None
        fields = {}
        for ctx in ctxs:
            if ctx is None:
                continue
            name = name or ctx.name
            for field in ctx.fields:
                fields.setdefault(field.name, field)
        return (
            None if name is None else Context(name=name, fields=list(fields.values()))
        )

    def _collect(
        self,
    ) -> Tuple[
        List[Tuple[Func, Optional[Context]]], Optional[Context], List[DecodeEntry]
    ]:
        """Build one function per decode/constraint snippet the decoder calls."""
        funcs = {}
        ctxs = {}
        for insn in self._driver.arch.instructions:
            enc = insn.encoding
            for name in enc.decode:
                if name not in funcs:
                    funcs[name] = Func.from_snippet(
                        snippet=self._driver.index.snippet[name],
                        index=self._driver.index,
                    )
                    ctxs[name] = None
            if enc.constraint_decode and enc.constraint_decode not in funcs:
                snippet = self._driver.index.snippet[enc.constraint_decode]
                funcs[enc.constraint_decode] = Func.from_snippet(
                    snippet=snippet,
                    index=self._driver.index,
                )
                ctxs[enc.constraint_decode] = self._snippet_ctx(snippet)

        entries = []
        for inst in self._driver.insts:
            ctx = ctxs.get(inst.constraint_decode)
            if ctx is None:
                call_args = "machInst"
            else:
                init = ", ".join(
                    f".{field.name} = {inst.const_value(field.name)}"
                    for field in ctx.fields
                )
                call_args = f"{ctx.name}{{{init}}}, machInst"
            entries.append(DecodeEntry(inst=inst, call_args=call_args))

        return (
            [(funcs[name], ctxs[name]) for name in funcs],
            self._union_ctx(ctxs.values()),
            entries,
        )

    def artifacts(self) -> Dict[Path, str]:
        num_operands = max((len(inst.regs) for inst in self._driver.insts), default=0)
        funcs, ctx, entries = self._collect()

        decoder_hh = _templates.render(
            name=Path("decoder.hh.jinja"),
            insts=self._driver.insts,
            num_operands=num_operands,
        )
        decoder_cc = _templates.render(
            name=Path("decoder.cc.jinja"), funcs=funcs, ctx=ctx, entries=entries
        )
        return {
            Path("decoder.hh"): decoder_hh,
            Path("decoder.cc"): decoder_cc,
        }

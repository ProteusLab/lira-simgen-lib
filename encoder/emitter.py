# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.instruction import Instruction
from lib.templates import Templates

import cpp.base_ops
from cpp.context import Context
from cpp.func import Func

_templates = Templates(Path(__file__).parent / "templates")

_CONTEXT_NAME = "EncCtx"


@dataclass
class EncodeEntry:
    inst: Instruction
    ctx: Optional[Context]

    @property
    def call_args(self) -> str:
        args = []
        if self.ctx:
            init = ", ".join(
                f".{field.name} = {self.inst.const_value(field.name)}"
                for field in self.ctx.fields
            )
            args.append(f"{self.ctx.name}{{{init}}}")
        args += [f"insn.operand{i}" for i in range(len(self.inst.operand_names))]
        return ", ".join(args)


class EncoderEmitter:
    def __init__(self, driver):
        self._driver = driver

    def artifacts(self) -> Dict[Path, str]:
        entries, snippets, ctx = self._collect()
        num_operands = max((len(inst.regs) for inst in self._driver.insts), default=0)

        isa_hh = _templates.render(
            name=Path("isa.hh.jinja"),
            insts=self._driver.insts,
            num_operands=num_operands,
        )

        encoder_hh = _templates.render(name=Path("encoder.hh.jinja"))
        encoder_cc = _templates.render(
            name=Path("encoder.cc.jinja"), funcs=entries, snippets=snippets, ctx=ctx
        )

        return {
            Path("isa.hh"): isa_hh,
            Path("encoder.hh"): encoder_hh,
            Path("encoder.cc"): encoder_cc,
        }

    def _collect(self) -> Tuple[List[EncodeEntry], List[Func], Optional[Context]]:
        entries = []
        funcs = {}
        ctxs = {}

        for inst in self._driver.insts:
            if not inst.encode_snippet:
                raise ValueError(f"{inst.name}: instruction has no encode snippet")

            name = inst.encode_snippet
            if name not in funcs:
                snippet = self._driver.index.snippet[name]
                funcs[name] = Func.from_snippet(
                    snippet=snippet, index=self._driver.index
                )
                ctxs[name] = self._snippet_ctx(snippet)

            entries.append(EncodeEntry(inst=inst, ctx=ctxs[name]))

        return entries, list(funcs.values()), Context.union(ctxs.values())

    @staticmethod
    def _snippet_ctx(snippet) -> Optional[Context]:
        fields = Func.dyn_fields(snippet)
        if not fields:
            return None
        return Context(name=_CONTEXT_NAME, fields=fields)

# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.instruction import Instruction
from lib.templates import Templates

import cpp.base_ops
from cpp.func import Context, Func

_templates = Templates(Path(__file__).parent / "templates")


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
        entries, snippets = self._collect()
        ctx = self._union_ctx(snippets)
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

    def _collect(self) -> Tuple[List[EncodeEntry], List[Func]]:
        entries = []
        funcs = {}

        for inst in self._driver.insts:
            if not inst.encode_snippet:
                raise ValueError(f"{inst.name}: instruction has no encode snippet")

            if inst.encode_snippet not in funcs:
                funcs[inst.encode_snippet] = Func.from_encode_snippet(
                    snippet=self._driver.index.snippet[inst.encode_snippet],
                    index=self._driver.index,
                )

            entries.append(EncodeEntry(inst=inst, ctx=funcs[inst.encode_snippet].ctx))

        return entries, list(funcs.values())

    @staticmethod
    def _union_ctx(snippets: List[Func]) -> Optional[Context]:
        name = None
        fields = {}

        for func in snippets:
            if func.ctx is None:
                continue
            if name is None:
                name = func.ctx.name
            for field in func.ctx.fields:
                fields.setdefault(field.name, field)

        if name is None:
            return None
        return Context(name=name, fields=list(fields.values()))

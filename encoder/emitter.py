# lira-simgen-lib/encoder/emitter.py
# Code generation of the instruction encoder.

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from lib.instruction import Instruction
from lib.templates import Templates

import cpp.base_ops
from cpp.func import Func

_templates = Templates(Path(__file__).parent / "templates")


@dataclass
class EncodeEntry:
    inst: Instruction
    func: Func

    @property
    def signature(self) -> str:
        return self.func.param_list


class EncoderEmitter:
    def __init__(self, driver):
        self._driver = driver

    def artifacts(self) -> Dict[Path, str]:
        entries = self._collect()

        encoder_hh = _templates.render(Path("encoder.hh.jinja"), funcs=entries)
        encoder_cc = _templates.render(Path("encoder.cc.jinja"), funcs=entries)

        return {
            Path("encoder.hh"): encoder_hh,
            Path("encoder.cc"): encoder_cc,
        }

    def _collect(self) -> List[EncodeEntry]:
        entries = []

        for inst in self._driver.insts:
            if not inst.encode_snippet:
                raise ValueError(f"{inst.name}: instruction has no encode snippet")

            func = Func.from_encode_snippet(
                self._driver.index.snippet[inst.encode_snippet],
                self._driver.index,
                inst.insn.operand_names,
            )

            entries.append(EncodeEntry(inst, func=func))

        return entries

# lira-simgen-lib/cpp/isa.py
# C++ ISA naming conventions and the ISA header emitter.

from pathlib import Path
from typing import Dict

from cpp.emitter import BaseEmitter


class Isa:
    M_INSN = "insn"

    @staticmethod
    def operand(index: int) -> str:
        return f"{Isa.M_INSN}.operand{index}"


class IsaEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")

    def artifacts(self) -> Dict[Path, str]:
        num_operands = max(
            (len(inst.operands) for inst in self._driver.insts), default=0
        )
        return {
            Path("isa.hh"): self._templates.render(
                name=Path("isa.hh.jinja"),
                insts=self._driver.insts,
                num_operands=num_operands,
            )
        }

# lira-simgen-lib/interpreter/emitter.py

from pathlib import Path
from typing import List, Set, Tuple

import cpp.base_ops
import cpp.nodes  # noqa: F401  (registers the node renderers)

from lib.instruction import Instruction
from lib.nodes import EnvExec, render_nodes
from cpp.types import OperandType


class InterpEmitter:
    def __init__(self, config):
        self.cfg = config

    def _terminators(self, insts: List[Instruction]) -> Set[str]:
        terminators = set()
        for inst in insts:
            for node in inst.sem:
                if isinstance(node, EnvExec) and node.interface.is_terminator:
                    terminators.add(inst.name)
                    break

        return terminators

    def execute(self, insts: List[Instruction]) -> Tuple[str, str]:
        bodies = {inst.name: render_nodes(inst.sem) for inst in insts}
        operand_types = {
            inst.name: [OperandType.gen(op.width) for op in inst.regs] for inst in insts
        }
        exec_hh = self.cfg.templates.render(Path(f"{self.cfg.execute_hh}.jinja"))
        exec_cc = self.cfg.templates.render(
            Path(f"{self.cfg.execute_cc}.jinja"),
            insts=insts,
            bodies=bodies,
            operand_types=operand_types,
            terminators=self._terminators(insts),
            m_cpu=self.cfg.M_CPU,
            m_mem=self.cfg.M_MEM,
        )
        return exec_hh, exec_cc

    def cpu_state(self, arch, interfaces, reg_files) -> Tuple[str, str]:
        from interpreter.interface import CpuInterface

        rf_code = "\n".join(reg_files[rf.name].definition for rf in arch.register_files)
        decls = [
            interface.declaration
            for interface in interfaces
            if isinstance(interface, CpuInterface)
        ]
        defs = "\n\n".join(
            interface.definition
            for interface in interfaces
            if isinstance(interface, CpuInterface) and interface.definition
        )
        cpu_hh = self.cfg.templates.render(
            Path(f"{self.cfg.cpu_state_hh}.jinja"), rf_code=rf_code, decls=decls
        )
        cpu_cc = self.cfg.templates.render(
            Path(f"{self.cfg.cpu_state_cc}.jinja"), defs=defs
        )
        return cpu_hh, cpu_cc

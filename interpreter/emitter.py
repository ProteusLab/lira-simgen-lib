# lira-simgen-lib/interpreter/emitter.py

from pathlib import Path
from typing import Dict, List, Set, Tuple

import cpp.base_ops
import cpp.nodes  # noqa: F401  (registers the node renderers)

import interpreter.nodes  # noqa: F401  (interpreter-specific renderers)

from cpp.emitter import BaseEmitter
from cpp.isa import Isa
from cpp.types import OperandType
from lib.instruction import Instruction
from lib.nodes import EnvCall, render_nodes

from interpreter.interface import CpuInterface, MemInterface, m_cpu, m_mem


class InterpEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        m_cpu.bind(driver.interfaces, CpuInterface)
        m_mem.bind(driver.interfaces, MemInterface)

    def _terminators(self, insts: List[Instruction]) -> Set[str]:
        terminators = set()
        for inst in insts:
            for node in inst.sem:
                if isinstance(node, EnvCall) and node.interface.is_terminator:
                    terminators.add(inst.name)
                    break

        return terminators

    def artifacts(self) -> Dict[Path, str]:
        insts = self._driver.insts

        bodies = {inst.name: render_nodes(inst.sem) for inst in insts}
        operand_types = {
            inst.name: [OperandType.gen(op.width) for op in inst.operands]
            for inst in insts
        }

        exec_hh = self._templates.render(name=Path("execute.hh.jinja"))
        exec_cc = self._templates.render(
            name=Path("execute.cc.jinja"),
            insts=insts,
            bodies=bodies,
            operand_types=operand_types,
            terminators=self._terminators(insts),
            isa=Isa,
            m_cpu=m_cpu,
            m_mem=m_mem,
        )

        cpu_hh, cpu_cc = self._cpu_state()

        return {
            Path("execute.hh"): exec_hh,
            Path("execute.cc"): exec_cc,
            Path("cpu_state.hh"): cpu_hh,
            Path("cpu_state.cc"): cpu_cc,
        }

    def _cpu_state(self) -> Tuple[str, str]:
        arch = self._driver.arch
        interfaces = self._driver.interfaces
        reg_files = self._driver.reg_files

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

        cpu_hh = self._templates.render(
            name=Path("cpu_state.hh.jinja"), rf_code=rf_code, decls=decls
        )
        cpu_cc = self._templates.render(name=Path("cpu_state.cc.jinja"), defs=defs)
        return cpu_hh, cpu_cc

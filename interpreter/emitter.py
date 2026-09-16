# lira-simgen-lib/interpreter/emitter.py

from typing import Dict, List, Set, Tuple

import lib.cpp.nodes  # noqa: F401  # activate the C++ node rendering
import lib.cpp.base_ops  # noqa: F401  # activate the operation bodies
import interpreter.Target.RISC_V.base_ops  # noqa: F401  # target shifts

from lib.cpp.func import Func
from lib.instruction import Instruction
from lib.nodes import EnvExec, render_nodes

from lib.interface import CpuInterface
from interpreter.interface import SetPC, SysCall


def _terminators(insts: List[Instruction]) -> Set[str]:
    return {
        inst.name
        for inst in insts
        if any(
            isinstance(node, EnvExec) and isinstance(node.interface, (SetPC, SysCall))
            for node in inst.sem
        )
    }


class InterpEmitter:
    def __init__(self, config):
        self.cfg = config

    def isa(self, insts: List[Instruction]) -> str:
        terminators = _terminators(insts)
        num_operands = max((len(inst.regs) for inst in insts), default=0)
        ilens = {inst.name: inst.lira_insn.encoding.encoded_size // 8 for inst in insts}
        return self.cfg.templates.render(
            self.cfg.isa_hh_jinja,
            insts=insts,
            terminators=terminators,
            ilens=ilens,
            num_operands=num_operands,
        )

    def decoder(self, index, insts: List[Instruction]) -> Tuple[str, str]:
        return (
            self.cfg.templates.render(self.cfg.decoder_hh_jinja),
            self.cfg.templates.render(self.cfg.decoder_cc_jinja, insts=insts),
        )

    def interpreter(self, insts: List[Instruction]) -> Tuple[str, str]:
        bodies = {inst.name: render_nodes(inst.sem) for inst in insts}
        return (
            self.cfg.templates.render(self.cfg.interpreter_hh_jinja),
            self.cfg.templates.render(
                self.cfg.interpreter_cc_jinja,
                insts=insts,
                bodies=bodies,
                cpu_var=self.cfg.CPU_VAR,
                mem_var=self.cfg.MEM_VAR,
            ),
        )

    def cpu_state(self, arch, interfaces, reg_files) -> Tuple[str, str]:
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
        return (
            self.cfg.templates.render(
                self.cfg.cpu_state_hh_jinja, rf_code=rf_code, decls=decls
            ),
            self.cfg.templates.render(self.cfg.cpu_state_cc_jinja, defs=defs),
        )

    def base_ops(self, operations) -> Tuple[str, str]:
        funcs = [Func.from_op(op) for op in operations]

        decls = "\n".join(f.declaration for f in funcs)
        defs = "\n".join(f.definition for f in funcs)
        return (
            self.cfg.templates.render(self.cfg.base_ops_hh_jinja, decls=decls),
            self.cfg.templates.render(self.cfg.base_ops_cc_jinja, defs=defs),
        )

    def snippets(self, funcs) -> Tuple[str, str]:
        decls = "\n".join(func.declaration for func in funcs)
        defs = "\n\n".join(func.definition for func in funcs)
        return (
            self.cfg.templates.render(self.cfg.snippets_hh_jinja, decls=decls),
            self.cfg.templates.render(self.cfg.snippets_cc_jinja, defs=defs),
        )

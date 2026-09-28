# lira-simgen-lib/lib/driver.py

from pathlib import Path
from typing import Dict, List

from lira.arch_ser_yaml import read_arch
from lira.arch_utils import build_arch_index

from lib.builders import SemanticBuilder
from lib.cpp.func import Func
from lib.instruction import Instruction
from lib.interface import InterfacesRegistry
from lib.regfile import RegFileRegistry


class Driver:
    def __init__(self, ir_path: Path, config):
        self.arch = read_arch(ir_path)
        self.index = build_arch_index(self.arch)

        registry = RegFileRegistry.from_arch(self.arch)
        self.reg_files = registry.reg_files

        self.attributes = self.process_attributes()

        self.interfaces = InterfacesRegistry.from_arch(self.arch, self.attributes)

        self.config = config
        self.fops = {f.name: f for f in self.arch.float_operations}

        supported = self.config.supported_instructions
        insns = [
            insn
            for insn in self.arch.instructions
            if (supported is None or insn.name in supported)
            and insn.name not in self.config.excluded_instructions
        ]
        self.snippet_funcs = self.process_snippets(insns)
        self.insts = self.process_instrs(insns)

    def process_attributes(self) -> Dict[str, object]:
        attributes: Dict[str, object] = {}
        for rf in self.arch.register_files:
            model = self.reg_files[rf.name]
            for reg in rf.regs:
                for attribute in reg.attributes:
                    if attribute:
                        attributes[attribute] = model.register(reg)
        return attributes

    def used_snippets(self, insns) -> List[str]:
        """Snippets a simulator needs: decoders, decode constraints and the
        semantics of snippet-defined operations (transitively). Encoders are
        not needed."""
        pending = []
        for insn in insns:
            pending += list(insn.encoding.decode)
            if insn.encoding.constraint_decode:
                pending.append(insn.encoding.constraint_decode)
            pending += self._op_snippets(insn.semantic)
        used = set()
        while pending:
            name = pending.pop()
            if name in used:
                continue
            used.add(name)
            pending += self._op_snippets(self.index.snippet[name].seq)
        return [name for name in self.index.snippet if name in used]

    def _op_snippets(self, seq) -> List[str]:
        return [
            self.index.op[stmt.specifier].semantic_func
            for stmt in seq.stmts
            if stmt.kind in ("op", "fold") and self.index.op[stmt.specifier].semantic_func
        ]

    def process_snippets(self, insns) -> List[Func]:
        return [
            Func.from_snippet(self.index.snippet[name], self.index)
            for name in self.used_snippets(insns)
        ]

    def process_instrs(self, insns) -> List[Instruction]:
        insts = []
        for i, insn in enumerate(insns):
            sem = SemanticBuilder(
                self.index,
                insn,
                self.interfaces,
                self.reg_files,
                self.fops,
                self.config.fpu_model,
            )
            body = sem.build(insn.semantic)
            insts.append(
                Instruction(
                    i,
                    body,
                    sem.regs,
                    len(sem.read_operands),
                    len(sem.write_operands),
                    sem.has_mem,
                    insn=insn,
                )
            )
        return insts

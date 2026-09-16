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

        self.snippet_funcs = self.process_snippets()

        self.config = config

        supported = self.config.supported_instructions
        self.insts = self.process_instrs(
            [
                insn
                for insn in self.arch.instructions
                if (supported is None or insn.name in supported)
                and insn.name not in self.config.excluded_instructions
            ],
        )

    def process_attributes(self) -> Dict[str, object]:
        attributes: Dict[str, object] = {}
        for rf in self.arch.register_files:
            model = self.reg_files[rf.name]
            for reg in rf.regs:
                for attribute in reg.attributes:
                    if attribute:
                        attributes[attribute] = model.register(reg)
        return attributes

    def process_snippets(self) -> List[Func]:
        return [
            Func.from_snippet(snippet, self.index)
            for snippet in self.index.snippet.values()
        ]

    def process_instrs(self, insns) -> List[Instruction]:
        insts = []
        for i, insn in enumerate(insns):
            sem = SemanticBuilder(self.index, insn, self.interfaces, self.reg_files)
            body = sem.build(insn.semantic)
            insts.append(
                Instruction(
                    i,
                    insn.name.upper(),
                    insn.encoding.constraint_decode,
                    body,
                    sem.regs,
                    len(sem.read_operands),
                    len(sem.write_operands),
                    sem.has_mem,
                    lira_insn=insn,
                )
            )
        return insts

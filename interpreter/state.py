"""Bind LIRA register files and environment functions to the target runtime."""

import re

from lira.arch import EnvironmentFunction

from interpreter import Target
from interpreter.interface import CpuInterface
from interpreter.regfile import RegisterFile, ScalableRegFile, attributes


class State:
    def __init__(self, arch, target, *, register_models=None, environment_models=None):
        """Bind architecture resources, optionally overriding models by name."""
        self.target = target
        info = Target.load(target)
        self.lane_multipliers = info.lane_multipliers
        register_models = info.register_models | (register_models or {})
        self.registers = {}
        for rf in arch.register_files:
            default = ScalableRegFile if rf.reg_size.lanes_mult is not None else RegisterFile
            self.registers[rf.name] = register_models.get(rf.name, default)(rf, self.lane_multipliers)
        for rf in arch.register_files:
            for attr in attributes(rf):
                alias = re.fullmatch(r"alias\.(\w+)@0\+(\d+)", attr)
                if alias is not None and alias[1] in self.registers:
                    model = self.registers[alias[1]]
                    if int(alias[2]) != model.file.reg_size.lanes_base:
                        raise ValueError(f"Alias width does not match register file {alias[1]}")
                    model.alias = self.registers[rf.name]
        pc = next((reg for reg in self.registers.values() if reg.pc), None)
        self.pc_field = pc.field if pc is not None else "m_pc"
        self.define_pc = pc is None
        self.cpu_members = "\n".join(filter(None, [
            info.cpu_members,
            *("  " + text for name, text in info.optional_cpu_members.items()
              if name not in self.registers),
        ]))

        functions = {function.name: function for function in arch.environment_functions}
        for name, (inputs, outputs) in info.runtime_functions.items():
            functions.setdefault(name, EnvironmentFunction(name, [], list(inputs), list(outputs)))
        models = info.environment_models | (environment_models or {})
        linked = {
            attribute: self.registers[rf.name].register(reg)
            for rf in arch.register_files
            for reg in rf.regs
            for attribute in attributes(reg)
        }
        self.environment = {}
        for name, function in functions.items():
            if name in models:
                bindings = {key: linked[key] for key in attributes(function) if key in linked}
                self.environment[name] = models[name](function, **bindings)
            else:
                self.environment[name] = CpuInterface(function)

    def lane_count(self, shape, cpu):
        expression, _ = self.lane_multipliers[shape.lanes_mult]
        return f"({shape.lanes_base} * {expression.format(cpu=cpu)})"

    def register_macros(self):
        return ["LIRA_RF_" + re.sub(r"\W", "_", name) for name in self.registers]

    def function_declarations(self):
        return filter(None, (function.declaration() for function in self.environment.values()))

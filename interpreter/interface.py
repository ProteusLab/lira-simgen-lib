"""Environment calls to the generated CPU and runtime memory."""

from dataclasses import dataclass

from lira.arch import EnvironmentFunction

from shared import cpp
from shared.types import OperandType


@dataclass
class CpuInterface:
    function: EnvironmentFunction
    takes_memory: bool = False
    definition: str = ""

    def call(self, cpu, mem, args):
        args = ([mem] if self.takes_memory else []) + list(args)
        return f"{cpu}.{self.function.name}({', '.join(map(str, args))})"

    def declaration(self):
        types = [OperandType.gen(width) for width in self.function.outputs]
        result = types[0] if types else "void"
        if len(types) > 1:
            result = f"std::tuple<{', '.join(types)}>"
        params = [
            cpp.NamedValue(f"a{i}", OperandType.gen(width))
            for i, width in enumerate(self.function.inputs)
        ]
        if self.takes_memory:
            params.insert(0, cpp.NamedValue("mem", "memory::Memory&"))
        return cpp.Function(self.function.name, result, tuple(params), []).declaration()


@dataclass
class PcFunction:
    method: str
    definition: str = ""

    def call(self, cpu, mem, args):
        return f"{cpu}.{self.method}({', '.join(map(str, args))})"

    def declaration(self):
        return ""


@dataclass
class MemoryFunction:
    method: str
    width: int
    definition: str = ""

    def call(self, cpu, mem, args):
        return f"{mem}.{self.method}<{OperandType.gen(self.width)}>({', '.join(map(str, args))})"

    def declaration(self):
        return ""


def read_mem(function):
    return MemoryFunction("read", function.outputs[0])


def read_mem_no_fault(function):
    return MemoryFunction("readNoFault", function.outputs[0])


def write_mem(function):
    return MemoryFunction("write", function.inputs[1])

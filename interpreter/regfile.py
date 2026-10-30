# lira-simgen-lib/interpreter/regfile.py

# Interpreter CPU-state register-file model

from lib.regfile import IRegFile

from cpp.types import OperandType


class RegFile(IRegFile):
    @property
    def set_guard(self) -> str:
        return ""

    @property
    def get_guard(self) -> str:
        return ""

    @property
    def definition(self) -> str:
        rf = self.rf
        ctype = OperandType.gen(rf.reg_size.lanes_base)
        if len(rf.regs) == 1:
            return f"""{ctype} m_{rf.regs[0].name};"""

        return f"""
std::array<{ctype}, {len(rf.regs)}> m_{rf.name}{{}};

// Set register function for {rf.name}
template<std::integral T>
void set{rf.name}(const std::size_t reg, const T value) {{
    {self.set_guard}
    m_{rf.name}[reg] = value;
}}

// Read register function for {rf.name}
template<std::integral T>
T get{rf.name}(const std::size_t reg) const {{
    {self.get_guard}
    return static_cast<T>(m_{rf.name}[reg]);
}}
"""

"""Register-file models used by the generated CPU and semantic snippets."""

from lira.arch import RegisterFile as LiraRegisterFile

from shared.types import OperandType


def attributes(component):
    return {
        attr if isinstance(attr, str) else attr.name + (f"@{attr.value}" if attr.value else "")
        for attr in component.attributes
    }


class RegisterFile:
    def __init__(self, register_file: LiraRegisterFile, multipliers):
        self.file = register_file
        self.name = register_file.name
        self.alias = None
        shape = register_file.reg_size
        self.type = OperandType.gen(shape.lanes_base) if shape.lanes_mult is None else None

    @property
    def singleton(self):
        return len(self.file.regs) == 1

    @property
    def field(self):
        return f"m_{self.file.regs[0].name if self.singleton else self.name}"

    @property
    def pc(self):
        return self.singleton and "pc" in attributes(self.file.regs[0])

    def read(self, index, *, cpu="cpu"):
        if self.singleton:
            return f"{cpu}.{self.field}"
        return f"{cpu}.get{self.name}<{self.type}>({index})"

    def write(self, index, value, *, cpu="cpu"):
        if self.pc:
            return f"{cpu}.setPC({value});"
        if self.singleton:
            return f"{cpu}.{self.field} = {value};"
        return f"{cpu}.set{self.name}({index}, {value});"

    def read_vector(self, index, out, width, *, cpu="cpu"):
        return f"prot::vec::unpack<{width}>({out}, {self.read(index, cpu=cpu)});"

    def write_vector(self, index, value, width, *, cpu="cpu"):
        packed = f"prot::vec::pack<{self.type}, {width}>({value})"
        return self.write(index, packed, cpu=cpu)

    def register(self, reg):
        return reg

    @property
    def set_guard(self):
        return ""

    @property
    def get_guard(self):
        return ""

    def definition(self):
        if self.singleton:
            return f"// Register file: {self.name}\n{self.type} {self.field}{{}};"
        name = self.name
        count = len(self.file.regs)
        return f"""// Register file: {name}
std::array<{self.type}, {count}> m_{name}{{}};

template<class T> void set{name}(std::size_t reg, T value) {{
{self.set_guard}  m_{name}[reg] = static_cast<{self.type}>(value);
}}

template<class T> T get{name}(std::size_t reg) const {{
{self.get_guard}  return static_cast<T>(m_{name}[reg]);
}}"""


class ScalableRegFile(RegisterFile):
    """A byte-packed file with enough storage for the largest lane count."""

    def __init__(self, register_file: LiraRegisterFile, multipliers):
        super().__init__(register_file, multipliers)
        shape = register_file.reg_size
        self.max_bytes = (shape.lanes_base * multipliers[shape.lanes_mult][1] + 7) // 8

    def read_vector(self, index, out, width, *, cpu="cpu"):
        return f"prot::vec::load<{width}>({out}, {cpu}.reg{self.name}({index}));"

    def write_vector(self, index, value, width, *, cpu="cpu"):
        return f"prot::vec::store<{width}>({cpu}.reg{self.name}({index}), {value});"

    def definition(self):
        name = self.name
        count = len(self.file.regs)
        return f"""// Register file: {name}
std::array<std::array<uint8_t, {self.max_bytes}>, {count}> m_{name}{{}};
uint8_t *reg{name}(std::size_t reg) {{ return m_{name}[reg].data(); }}
const uint8_t *reg{name}(std::size_t reg) const {{ return m_{name}[reg].data(); }}"""

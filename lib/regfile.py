# lira-simgen-lib/lib/regfile.py

from abc import ABC
import re
from typing import ClassVar, Dict, Optional, Tuple

from lira.arch import Arch, RegisterFile

from lib.types import Lanes, OperandType


class IRegFile(ABC):
    def __init__(self, rf: Optional[RegisterFile] = None):
        self.rf: Optional[RegisterFile] = rf
        # (model of the file, width): the registers of this file are the low
        # `width` bits of that file's registers (`alias.<this>@0+<width>`)
        self.alias_of: Optional[Tuple["IRegFile", int]] = None

    def read(self, reg, var) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} does not provide register reads"
        )

    def write(self, reg, value) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} does not provide register writes"
        )

    def read_lanes(self, index, var, lane_width: int) -> str:
        """`var` = the register as lanes of `lane_width` bits (lane 0 in the
        low bits): read the whole register and split it."""
        reg_type = OperandType.gen(self.rf.reg_size.lanes_base)
        return f"""{{
  {reg_type} reg{{0}};
  {self.read(index, "reg")}
  prot::vec::unpack<{lane_width}>({var}, reg);
}}"""

    def write_lanes(self, index, value, lane_width: int) -> str:
        """Write the lanes of `value` (`lane_width` bits each) as the register."""
        reg_type = OperandType.gen(self.rf.reg_size.lanes_base)
        return f"""{{
  const {reg_type} reg = prot::vec::pack<{reg_type}, {lane_width}>({value});
  {self.write(index, "reg")}
}}
"""

    def wiring(self, reg) -> str:
        return ""

    def register(self, reg) -> object:
        return reg

    @property
    def definition(self) -> str:
        return ""


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
            return f"""\
  // Register file: {rf.name}
  {ctype} m_{rf.regs[0].name}{{}};
"""

        return f"""\
  // Register file: {rf.name}
  std::array<{ctype}, {len(rf.regs)}> m_{rf.name}{{}};

  // Set register function for {rf.name}
  template<std::integral T>
  void set{rf.name}(const std::size_t reg, const T value) {{
{self.set_guard}    m_{rf.name}[reg] = value;
  }}

  // Read register function for {rf.name}
  template<std::integral T>
  T get{rf.name}(const std::size_t reg) const {{
{self.get_guard}    return static_cast<T>(m_{rf.name}[reg]);
  }}
"""


class ScalableRegFile(IRegFile):
    """Registers of a scalable size (`<n>VQ` bits): the bytes of each register
    (little endian) in storage for the largest size; only the low bits of the
    current size are read. Shaped reads and writes see lanes; `reg<name>(i)`
    gives the bytes of register i."""

    @property
    def max_bytes(self) -> int:
        size = self.rf.reg_size
        return (Lanes.maximum(size.lanes_base, size.lanes_mult) + 7) // 8

    # Name of the CPU state in generated code
    cpu_var: ClassVar[str] = "cpu"

    def accessor(self, index) -> str:
        return f"{self.cpu_var}.reg{self.rf.name}({index})"

    def read_lanes(self, index, var, lane_width: int) -> str:
        return f"prot::vec::load<{lane_width}>({var}, {self.accessor(index)});"

    def write_lanes(self, index, value, lane_width: int) -> str:
        return f"prot::vec::store<{lane_width}>({self.accessor(index)}, {value});\n"

    @property
    def definition(self) -> str:
        rf = self.rf
        size = rf.reg_size
        return f"""\
  // Register file: {rf.name} ({len(rf.regs)} x {size.lanes_base}{size.lanes_mult} bits, at most {8 * self.max_bytes})
  std::array<std::array<uint8_t, {self.max_bytes}>, {len(rf.regs)}> m_{rf.name}{{}};
  uint8_t *reg{rf.name}(const std::size_t reg) {{ return m_{rf.name}[reg].data(); }}
  const uint8_t *reg{rf.name}(const std::size_t reg) const {{ return m_{rf.name}[reg].data(); }}
"""


def serves(name: str):
    def decorator(model_cls):
        RegFileRegistry.registry[name] = model_cls
        return model_cls

    return decorator


class RegFileRegistry:
    registry: ClassVar[Dict[str, type]] = {}

    def __init__(self):
        self.reg_files: Dict[str, IRegFile] = {}

    @classmethod
    def from_arch(cls, arch: Arch) -> "RegFileRegistry":
        reg = cls()
        for rf in arch.register_files:
            model_cls = cls.registry.get(rf.name)
            if model_cls is None:
                raise ValueError(f"no register-file model registered for '{rf.name}'")
            reg.reg_files[rf.name] = model_cls(rf)
        for rf in arch.register_files:
            for attribute in rf.attributes:
                m = re.fullmatch(r"alias\.(\w+)@0\+(\d+)", attribute)
                if m and m.group(1) in reg.reg_files:
                    reg.reg_files[m.group(1)].alias_of = (reg.reg_files[rf.name], int(m.group(2)))
        for name in cls.registry:
            if name not in reg.reg_files:
                print(
                    f"warning: register-file model '{name}' is registered "
                    f"but not present in the IR register files"
                )
        return reg

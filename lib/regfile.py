# lira-simgen-lib/lib/regfile.py

from abc import ABC
from typing import ClassVar, Dict, Optional

from lira.arch import Arch, RegisterFile

from lib.types import OperandType


class IRegFile(ABC):
    def __init__(self, rf: Optional[RegisterFile] = None):
        self.rf: Optional[RegisterFile] = rf

    def read(self, reg, var) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} does not provide register reads"
        )

    def write(self, reg, value) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} does not provide register writes"
        )

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
  {ctype} m_{rf.regs[0].name};
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


def serves(name: str):
    """Mark the register-file model class as serving the given IR
    register file name (registers it in RegFileRegistry.registry)."""

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
                raise ValueError(
                    f"no register-file model registered for '{rf.name}'"
                )
            reg.reg_files[rf.name] = model_cls(rf)
        for name in cls.registry:
            if name not in reg.reg_files:
                print(
                    f"warning: register-file model '{name}' is registered "
                    f"but not present in the IR register files"
                )
        return reg

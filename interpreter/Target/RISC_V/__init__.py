# lira-simgen-lib/interpreter/Target/RISC_V/__init__.py

from cpp.Target.RISC_V import base_ops  # noqa: F401

from interpreter.Target.RISC_V import interface, regfile  # noqa: F401
from interpreter.Target.RISC_V.regfile import XRegs  # noqa: F401
from interpreter.interface import m_cpu  # noqa: F401

m_cpu.getXRegs = XRegs
m_cpu.setXRegs = XRegs

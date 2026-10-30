# lira-simgen-lib/interpreter/Target/RISC_V/__init__.py

from interpreter.Target.RISC_V import interface, regfile
from cpp.Target.RISC_V import base_ops

MODULES = {
    "interface": interface,
    "regfile": regfile,
    "base_ops": base_ops,
}

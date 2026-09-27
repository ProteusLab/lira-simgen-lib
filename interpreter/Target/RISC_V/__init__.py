# lira-simgen-lib/interpreter/Target/RISC_V/__init__.py

import interpreter.Target.RISC_V.base_ops
import interpreter.Target.RISC_V.interface
import interpreter.Target.RISC_V.regfile

from interpreter.Target import TargetInfo

TARGET = TargetInfo(addr_type="uint32_t")

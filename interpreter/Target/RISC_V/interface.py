# lira-simgen-lib/interpreter/Target/RISC_V/interface.py

from lib.interface import serves

from interpreter.interface import (
    GetPC,
    ReadMem,
    SetPC,
    SysCall,
    WriteMem,
)

serves("readMem8")(ReadMem)
serves("readMem16")(ReadMem)
serves("readMem32")(ReadMem)
serves("writeMem8")(WriteMem)
serves("writeMem16")(WriteMem)
serves("writeMem32")(WriteMem)
serves("getPC")(GetPC)
serves("setPC")(SetPC)
serves("sysCall")(SysCall)

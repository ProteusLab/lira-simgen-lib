# lira-simgen-lib/interpreter/Target/RISC_V/interface.py

from cpp.context import serves

from interpreter.interface import (
    GetPC,
    ReadMem,
    SetPC,
    SysCall,
    WriteMem,
    m_cpu,
    m_mem,
)

# Protea ADL bindings
serves(m_mem)("readMem8", ReadMem)
serves(m_mem)("readMem16", ReadMem)
serves(m_mem)("readMem32", ReadMem)
serves(m_mem)("writeMem8", WriteMem)
serves(m_mem)("writeMem16", WriteMem)
serves(m_mem)("writeMem32", WriteMem)

serves(m_cpu)("getPC", GetPC)
serves(m_cpu)("setPC", SetPC)
serves(m_cpu)("sysCall", SysCall)

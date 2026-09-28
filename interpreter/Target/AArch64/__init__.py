# lira-simgen-lib/interpreter/Target/AArch64/__init__.py

import interpreter.Target.AArch64.interface
import interpreter.Target.AArch64.regfile

from interpreter.Target import TargetInfo

TARGET = TargetInfo(
    addr_type="uint64_t",
    # PC is not a LIRA register file in the AArch64 description: it is only
    # reachable through the `pc_read` / `pc_write` environment functions.
    cpu_members="""\
  // Program counter
  uint64_t m_pc{0};
  uint64_t getPC() const { return m_pc; }
  void setPC(uint64_t value) {
    m_pc = value;
    m_pcWritten = true;
  }

  // Local exclusive monitor (single PE): address and size marked by the last
  // load-exclusive
  bool m_exclValid{false};
  uint64_t m_exclAddr{0};
  uint8_t m_exclSize{0};
""",
)

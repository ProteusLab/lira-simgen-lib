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

  // EL0 system state: TPIDR_EL0 and the PSTATE.{DIT,SSBS} bits
  uint64_t m_tpidrEl0{0};
  bool m_dit{false};
  bool m_ssbs{false};

  // SVE vector length in quadwords (VL / 128, 1..16), fixed for a run; the
  // streaming vector length is the same
  std::size_t m_vq{1};
""",
    # `<n>VQ` lanes (SVE vectors and predicates) and `<n>VQVQ` (the ZA array)
    lane_multipliers={"VQ": "cpu.m_vq", "VQVQ": "cpu.m_vq * cpu.m_vq"},
)

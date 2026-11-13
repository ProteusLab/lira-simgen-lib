from interpreter.Target import TargetInfo
from interpreter.Target.AArch64.interface import INTERFACES, RUNTIME_FUNCTIONS
from interpreter.Target.AArch64.regfile import REGISTER_FILES


TARGET = TargetInfo(
    cpu_members="""\
  // Local exclusive monitor (single PE)
  bool m_exclValid{false};
  uint64_t m_exclAddr{0};
  uint8_t m_exclSize{0};

  // EL0 system state
  uint64_t m_tpidrEl0{0};
  bool m_dit{false};
  bool m_ssbs{false};

  // SVE and streaming vector length in quadwords
  std::size_t m_vq{1};""",
    optional_cpu_members={"FPCR": "uint32_t m_fpcr{0};", "FPSR": "uint32_t m_fpsr{0};"},
    lane_multipliers={"VQ": ("{cpu}.m_vq", 16), "VQVQ": ("{cpu}.m_vq * {cpu}.m_vq", 256)},
    register_models=REGISTER_FILES,
    environment_models=INTERFACES,
    runtime_functions=RUNTIME_FUNCTIONS,
)

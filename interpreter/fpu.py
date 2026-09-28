# lira-simgen-lib/interpreter/fpu.py

"""FPU state of `fop` statements: C++ helpers that build a prot::fp::State
from the control register and OR the raised flags into the status register.
The registers and bit positions come from the `fpu.*` register attributes
(lira.float_ops.FPUBinding)."""

from typing import Optional

from lira.arch import Arch
from lira.float_ops import FPUBinding

from interpreter import config

# LIRA flag name -> prot::fp flag constant (runtime/lira_fp.hh)
_FLAGS = {
    "invalid": "kInvalid",
    "divbyzero": "kDivByZero",
    "overflow": "kOverflow",
    "underflow": "kUnderflow",
    "inexact": "kInexact",
    "input_denormal": "kInputDenormal",
}

STATE_FN = "fpuState"
UPDATE_FN = "fpuUpdate"


class FpuModel:
    """How `fop` statements reach the FPU state in the generated interpreter."""

    def wrap(self, assignment: str) -> str:
        """Run `assignment` (a call using `fpu`) with the CPU's FPU state."""
        cpu = config.SimpleInterpConfig.CPU_VAR
        return f"""{{
  prot::fp::State fpu = {STATE_FN}({cpu});
  {assignment}
  {UPDATE_FN}({cpu}, fpu);
}}
"""

    @staticmethod
    def helpers(arch: Arch, reg_files) -> Optional[str]:
        """Definitions of fpuState(cpu) and fpuUpdate(cpu, st), or None when
        the description has no FPU binding."""
        binding = FPUBinding.from_arch(arch)
        if binding is None:
            return None
        cpu = config.SimpleInterpConfig.CPU_VAR
        (crf, ci), (srf, si) = binding.control, binding.status

        def field(name: str) -> str:
            if name not in binding.fields:
                return "0"
            lsb, width = binding.fields[name]
            return f"(control >> {lsb}) & {(1 << width) - 1}"

        flags = "\n".join(
            f"  if (st.flags & prot::fp::{_FLAGS[name]}) status |= uint64_t{{1}} << {bit};"
            for name, bit in sorted(binding.flag_bits.items(), key=lambda kv: kv[1])
        )
        return f"""\
// FPU controls for a float operation
prot::fp::State {STATE_FN}(const CPU &{cpu}) {{
  uint64_t control{{0}};
  {reg_files[crf].read(ci, "control")}
  prot::fp::State st;
  st.rmode = {field("rmode")};
  st.fz = {field("fz")};
  st.fz16 = {field("fz16")};
  st.dn = {field("dn")};
  return st;
}}

// Accumulate the flags raised by a float operation
void {UPDATE_FN}(CPU &{cpu}, const prot::fp::State &st) {{
  uint64_t status{{0}};
  {reg_files[srf].read(si, "status")}
{flags}
  {reg_files[srf].write(si, "status")}
}}
"""

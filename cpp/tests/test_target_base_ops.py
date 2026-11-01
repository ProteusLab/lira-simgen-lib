# lira-simgen-lib/cpp/tests/test_target_base_ops.py

from lira.ir_ops import Asr, DivS, Lsl, Lsr, RemS

import cpp.Target.RISC_V.base_ops  # noqa: F401  (applies the RISC-V overrides)


def test_shift_masks():
    assert Lsl(32)._cpp_body() == "  b &= 31;\n  return a << b;\n"
    assert Lsr(32)._cpp_body() == "  b &= 31;\n  return a >> b;\n"
    assert Lsl(64)._cpp_body() == "  b &= 63;\n  return a << b;\n"


def test_asr():
    assert Asr(32)._cpp_body() == """\
  b &= 31;
  return (uint32_t)((int32_t)a >> b);
"""


def test_div_s_overflow_guard():
    assert DivS(32)._cpp_body() == """\
  if (b == 0) return c;
  if ((uint32_t)a == (uint32_t)1 << 31 && (int32_t)b == -1) return a;
  return (uint32_t)((int32_t)a / (int32_t)b);
"""


def test_rem_s_overflow_guard():
    assert RemS(32)._cpp_body() == """\
  if (b == 0) return a;
  if ((uint32_t)a == (uint32_t)1 << 31 && (int32_t)b == -1) return 0;
  int32_t res = (int32_t)a % (int32_t)b;
  return (uint32_t)res;
"""

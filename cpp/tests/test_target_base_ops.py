# lira-simgen-lib/cpp/tests/test_target_base_ops.py

from lira.ir_ops import Asr, DivS, Lsl, Lsr, RemS

import cpp.Target.RISC_V.base_ops


def test_shift_masks():
    assert Lsl(32)._cpp_body() == """arg1 &= 31;
return arg0 << arg1;
"""

    assert Lsr(32)._cpp_body() == """arg1 &= 31;
return arg0 >> arg1;
"""

    assert Lsl(64)._cpp_body() == """arg1 &= 63;
return arg0 << arg1;
"""


def test_asr():
    assert Asr(32)._cpp_body() == """arg1 &= 31;
return (uint32_t)((int32_t)arg0 >> arg1);
"""


def test_div_s_overflow_guard():
    assert DivS(32)._cpp_body() == """if (arg1 == 0) return arg2;
if ((uint32_t)arg0 == (uint32_t)1 << 31 && (int32_t)arg1 == -1) return arg0;
return (uint32_t)((int32_t)arg0 / (int32_t)arg1);
"""


def test_rem_s_overflow_guard():
    assert RemS(32)._cpp_body() == """if (arg1 == 0) return arg0;
if ((uint32_t)arg0 == (uint32_t)1 << 31 && (int32_t)arg1 == -1) return 0;
int32_t res = (int32_t)arg0 % (int32_t)arg1;
return (uint32_t)res;
"""

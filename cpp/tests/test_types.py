# lira-simgen-lib/cpp/tests/test_types.py

import pytest

from cpp.types import OperandType


@pytest.mark.parametrize(
    "width, expected",
    [
        (1, "bool"),
        (8, "uint8_t"),
        (16, "uint16_t"),
        (32, "uint32_t"),
        (64, "uint64_t"),
        (128, "uint128_t"),
    ],
)
def test_gen_unsigned(width, expected):
    assert OperandType.gen(width) == expected


@pytest.mark.parametrize(
    "width, expected",
    [
        (8, "int8_t"),
        (16, "int16_t"),
        (32, "int32_t"),
        (64, "int64_t"),
    ],
)
def test_gen_signed(width, expected):
    assert OperandType.gen(width, signed=True) == expected


@pytest.mark.parametrize(
    "width, expected",
    [
        (1, 1),
        (2, 8),
        (7, 8),
        (9, 16),
        (16, 16),
        (17, 32),
        (33, 64),
        (65, 128),
        (128, 128),
    ],
)
def test_bits(width, expected):
    assert OperandType.bits(width) == expected

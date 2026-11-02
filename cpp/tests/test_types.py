# lira-simgen-lib/cpp/tests/test_types.py

import pytest

from cpp.types import OperandType


@pytest.mark.parametrize(
    "width, expected",
    [
        (1, OperandType.BOOL),
        (8, OperandType.U8),
        (16, OperandType.U16),
        (32, OperandType.U32),
        (64, OperandType.U64),
        (128, OperandType.U128),
    ],
)
def test_gen_unsigned(width, expected):
    assert OperandType.gen(width) == expected


@pytest.mark.parametrize(
    "width, expected",
    [
        (8, OperandType.I8),
        (16, OperandType.I16),
        (32, OperandType.I32),
        (64, OperandType.I64),
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

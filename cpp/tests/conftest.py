# lira-simgen-lib/cpp/tests/conftest.py

import pytest

from lira.arch import (
    EnvironmentFunction,
    Instruction,
    InstructionEncoding,
    Register,
    RegisterFile,
)
from lira.arch_utils import build_arch_index
from lira.ir import Shape, StatementSeq
from lira.ir_builder import ArchBuilder, SnippetBuilder
from lira.ir_ops import Add, And, Eq, ExtractLow, Lsl, Orr

import cpp.base_ops  # noqa: F401  (registers the generic C++ operation bodies)
import cpp.Target.RISC_V.base_ops  # noqa: F401  (applies the RISC-V overrides)


@pytest.fixture
def arch():
    builder = ArchBuilder(name="TestArch", attributes=[])

    regs = [Register(f"x{i}", []) for i in range(4)]
    builder.add_register_file(RegisterFile("XRegs", [], Shape(32, None), regs))
    builder.add_register_file(
        RegisterFile("ProgramCounter", [], Shape(32, None), [Register("pc", ["pc"])])
    )
    builder.add_env_func(EnvironmentFunction("sysCall", [], [], []))

    for op in (Add(32), ExtractLow(32, 5), Lsl(32), Orr(32), And(32), Eq(32)):
        builder.add_operation(op)

    sb = SnippetBuilder(name="decode_0")
    raw = sb.input(0, 32)
    low = sb.extract_low(raw, 5)
    sb.output(low, 0)
    builder.add_snippet(sb.build())

    eb = SnippetBuilder(name="encode_0")
    a = eb.input(0, 32)
    c = eb.input(1, 32)
    word = eb.orr(eb.lsl(c, eb.const(7, 32)), a)
    eb.output(word, 0)
    builder.add_snippet(eb.build())

    cb = SnippetBuilder(name="constraint_0")
    r = cb.input(0, 32)
    masked = cb.and_(r, cb.const(0xFF, 32))
    match = cb.eq(masked, cb.const(0x33, 32))
    cb.output(match, 0)
    builder.add_snippet(cb.build())

    enc = InstructionEncoding(
        encoded_size=32,
        const_encoding_part=0x33,
        const_mask=0xFF,
        decode=["decode_0"],
        encode="encode_0",
        constraint_decode="constraint_0",
        constraint_encode="",
    )
    insn = Instruction(
        name="add",
        attributes=[],
        operand_sizes=[32, 32],
        operand_names=["rs1", "rd"],
        encoding=enc,
        semantic=StatementSeq([]),
    )
    builder.add_instruction(insn)
    return builder.build()


@pytest.fixture
def index(arch):
    return build_arch_index(arch)

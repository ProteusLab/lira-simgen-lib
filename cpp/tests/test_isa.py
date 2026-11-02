# lira-simgen-lib/cpp/tests/test_isa.py

import pytest

from lira.arch import InstructionEncoding, Register, RegisterFile
from lira.arch import Instruction as LiraInstruction
from lira.ir import Shape, StatementSeq
from lira.ir_builder import ArchBuilder

from cpp.isa import addr_type_of, render_isa
from lib.instruction import Instruction
from lib.operand import Register as OperandRegister
from lira.arch import Snippet


def make_instruction(name, regs):
    enc = InstructionEncoding(
        encoded_size=32,
        const_encoding_part=0,
        const_mask=0,
        decode=[],
        encode="",
        constraint_decode="",
        constraint_encode="",
    )
    insn = LiraInstruction(
        name=name,
        attributes=[],
        operand_sizes=[r.width for r in regs],
        operand_names=[r.name for r in regs],
        encoding=enc,
        semantic=StatementSeq([]),
    )
    return Instruction([], regs, insn)


def test_addr_type_of(arch):
    assert addr_type_of(arch) == "uint32_t"


def test_addr_type_of_missing_pc():
    builder = ArchBuilder(name="NoPC", attributes=[])
    builder.add_register_file(
        RegisterFile("XRegs", [], Shape(32, None), [Register("x0", [])])
    )
    with pytest.raises(ValueError):
        addr_type_of(builder.build())


def test_render_isa_addr_parametrized():
    reg = OperandRegister("rd", 32, Snippet("dummy", StatementSeq([])))
    inst = make_instruction("add", [reg])
    out = render_isa([inst], "uint64_t")
    assert "using Addr = uint64_t;" in out
    assert "using Word = uint32_t;" in out
    assert "kADD" in out
    assert "operand0" in out
    assert "return 4;" in out

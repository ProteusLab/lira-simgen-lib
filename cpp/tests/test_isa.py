# lira-simgen-lib/cpp/tests/test_isa.py

from pathlib import Path
from types import SimpleNamespace

from cpp.isa import Isa, IsaEmitter


def test_m_insn():
    assert Isa.M_INSN == "insn"


def test_operand():
    assert Isa.operand(0) == "insn.operand0"
    assert Isa.operand(2) == "insn.operand2"


def test_isa_emitter_init():
    emitter = IsaEmitter(None)
    assert emitter._driver is None


def test_isa_emitter_artifacts():
    driver = SimpleNamespace(
        arch=SimpleNamespace(
            register_files=[
                SimpleNamespace(
                    reg_size=SimpleNamespace(lanes_base=32),
                    regs=[SimpleNamespace(attributes=["pc"])],
                )
            ]
        ),
        insts=[SimpleNamespace(name="ADD", ilen=4, operands=[0, 0])],
    )
    out = IsaEmitter(driver).artifacts()
    assert set(out) == {Path("isa.hh")}
    text = out[Path("isa.hh")]
    assert "GENERATED_LIRA_ISA_HH_INCLUDED" in text
    assert "enum class Opcode" in text
    assert "kADD," in text
    assert "using Addr = uint32_t;" in text
    assert "uint32_t operand0;" in text
    assert "uint32_t operand1;" in text
    assert "case Opcode::kADD: return 4;" in text


def test_isa_emitter_addr64():
    driver = SimpleNamespace(
        arch=SimpleNamespace(
            register_files=[
                SimpleNamespace(
                    reg_size=SimpleNamespace(lanes_base=64),
                    regs=[SimpleNamespace(attributes=["pc"])],
                )
            ]
        ),
        insts=[SimpleNamespace(name="ADD", ilen=4, operands=[0, 0])],
    )
    text = IsaEmitter(driver).artifacts()[Path("isa.hh")]
    assert "using Addr = uint64_t;" in text


def test_isa_emitter_default_addr():
    driver = SimpleNamespace(
        arch=SimpleNamespace(register_files=[]),
        insts=[SimpleNamespace(name="ADD", ilen=4, operands=[0, 0])],
    )
    text = IsaEmitter(driver).artifacts()[Path("isa.hh")]
    assert "using Addr = uint32_t;" in text

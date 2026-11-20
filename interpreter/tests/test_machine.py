from itertools import permutations

import pytest

from lira.arch import Register, RegisterFile
from lira.ir import Shape, Statement, StatementSeq
from lira.ir_builder import ArchBuilder

from interpreter import Machine


@pytest.fixture(params=permutations(("Z", "V", "D")))
def arch(request):
    files = {
        "Z": (Shape(128, "VQ"), ["alias.V@0+128"]),
        "V": (Shape(128, None), ["alias.D@0+64"]),
        "D": (Shape(64, None), []),
    }
    builder = ArchBuilder("VectorAliases", [])
    for name in request.param:
        shape, attributes = files[name]
        builder.add_register_file(
            RegisterFile(name, attributes, shape, [Register("r0"), Register("r1")])
        )
    return builder.build()


@pytest.fixture(params=(1, 4))
def machine(arch, request):
    return Machine(arch, vq=request.param)


def test_vector_alias_chain_shares_storage(machine):
    machine.regs["Z"][1] = (1 << (128 * machine.vq)) - 1
    assert machine.regs["V"][1] == (1 << 128) - 1
    assert machine.regs["D"][1] == (1 << 64) - 1

    machine.regs["D"][1] = 0x0123456789ABCDEF
    assert machine.regs["Z"][1] == 0x0123456789ABCDEF
    assert machine.regs["V"][1] == 0x0123456789ABCDEF
    assert all(machine.regs[name][0] == 0 for name in ("Z", "V", "D"))


def test_vector_alias_read_write_lanes(machine):
    scalar, vector = Shape(1, None), Shape(4, None)
    machine.regs["Z"][1] = (1 << (128 * machine.vq)) - 1
    seq = StatementSeq(
        [
            Statement(scalar, ["index"], [1], "const", "1", []),
            Statement(vector, ["value"], [32], "input", "0", []),
            Statement(vector, [], [], "write", "V", ["index", "value"]),
            Statement(Shape(2, None), ["d"], [32], "read", "D", ["index"]),
            Statement(Shape(4, "VQ"), ["z"], [32], "read", "Z", ["index"]),
            Statement(scalar, [], [], "output", "0", ["d"]),
            Statement(scalar, [], [], "output", "1", ["z"]),
        ]
    )
    lanes = [0xDEADBEEF, 0x01234567, 0x89ABCDEF, 0x76543210]
    assert machine.run(seq, [lanes]) == [
        lanes[:2],
        lanes + [0] * (4 * machine.vq - 4),
    ]


def test_alias_cycle_is_rejected():
    builder = ArchBuilder("CyclicAliases", [])
    for name, other in (("V", "D"), ("D", "V")):
        builder.add_register_file(
            RegisterFile(
                name, [f"alias.{other}@0+64"], Shape(64, None), [Register("r0")]
            )
        )
    with pytest.raises(ValueError, match="cyclic register file alias"):
        Machine(builder.build())

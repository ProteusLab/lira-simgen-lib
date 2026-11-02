# lira-simgen-lib/cpp/tests/test_nodes.py

import pytest

from lira.arch import Snippet
from lira.ir import StatementSeq
from lira.ir_ops import Add

import cpp.nodes  # noqa: F401  (registers the node renderers)

from lib.nodes import (
    EnvExec,
    Input,
    NodeImpl,
    Op,
    ReadMem,
    ReadReg,
    Return,
    WriteReg,
    render_nodes,
)
from lib.operand import Constant, Register, Variable


class SimpleRegFile:
    def read(self, reg, var):
        return f"{var} = m_xregs[{reg.name}];"

    def write(self, reg, value):
        return f"m_xregs[{reg.name}] = {value};"


class SimpleInterface:
    def __call__(self, inputs, out):
        if out is None:
            return f"mem.write({', '.join(str(i) for i in inputs)});"
        return f"{out} = mem.read({', '.join(str(i) for i in inputs)});"


def make_register(name, rf):
    return Register(name, 32, Snippet("dummy", StatementSeq([])), rf=rf)


def test_constant():
    assert render_nodes([Constant("_t1", 32, "51")]) == "uint32_t _t1 = 51;"


def test_input():
    var = Variable("_t1", 32)
    source = Variable("arg0", 32)
    assert render_nodes([Input(var, source)]) == "uint32_t _t1{0};\n_t1 = arg0;\n"


def test_op():
    out = Variable("_t2", 32)
    a = Variable("a", 32)
    b = Variable("b", 32)
    assert render_nodes([Op(out, Add(32), [a, b])]) == """\
uint32_t _t2{0};
_t2 = add_32(a, b);
"""


def test_read_reg():
    reg = make_register("rd", SimpleRegFile())
    var = Variable("_t1", 32)
    assert render_nodes([ReadReg(reg, var)]) == """\
uint32_t _t1{0};
_t1 = m_xregs[rd];
"""


def test_write_reg():
    reg = make_register("rd", SimpleRegFile())
    value = Variable("_t2", 32)
    assert render_nodes([WriteReg(reg, value)]) == "m_xregs[rd] = _t2;"


def test_read_mem():
    var = Variable("_t1", 32)
    addr = Variable("a", 32)
    assert render_nodes([ReadMem(var, [addr], SimpleInterface())]) == """\
uint32_t _t1{0};
_t1 = mem.read(a);
"""


def test_env_exec():
    a = Variable("a", 32)
    b = Variable("b", 32)
    assert render_nodes([EnvExec([a, b], SimpleInterface())]) == "mem.write(a, b);"


def test_return():
    assert render_nodes([Return(Variable("_t1", 32))]) == "return _t1;"


def test_unrendered_node():
    with pytest.raises(NotImplementedError):
        render_nodes([object()])


def test_render_nodes_joins():
    nodes = [Constant("_t1", 32, "1"), Return(Variable("_t1", 32))]
    assert render_nodes(nodes) == "uint32_t _t1 = 1;\nreturn _t1;"
    assert len(NodeImpl._impl) >= 8

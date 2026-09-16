# lira-simgen-lib/lib/cpp/nodes.py

from .. import nodes
from . import base_ops  # noqa: F401  # activate the operation bodies
from .func import Func


def _include() -> None:
    nodes.InputAssign.cpp_body = _InputAssignBody.cpp_body
    nodes.OpAssign.cpp_body = _OpAssignBody.cpp_body
    nodes.ReadReg.cpp_body = _ReadRegBody.cpp_body
    nodes.WriteReg.cpp_body = _WriteRegBody.cpp_body
    nodes.ReadMem.cpp_body = _ReadMemBody.cpp_body
    nodes.EnvExec.cpp_body = _EnvExecBody.cpp_body
    nodes.MemberAssign.cpp_body = _MemberAssignBody.cpp_body
    nodes.Return.cpp_body = _ReturnBody.cpp_body


class _InputAssignBody:
    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.var} = {self.source};
"""


class _OpAssignBody:
    def cpp_body(self) -> str:
        return f"""{self.out.definition}
{self.out} = {Func.from_op(self.op)([a.name for a in self.args])};
"""


class _ReadRegBody:
    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.reg.read(self.var)}
"""


class _WriteRegBody:
    def cpp_body(self) -> str:
        return self.reg.write(self.value)


class _ReadMemBody:
    def cpp_body(self) -> str:
        return f"""{self.var.definition}
{self.interface(self.inputs, self.var)}
"""


class _EnvExecBody:
    def cpp_body(self) -> str:
        return self.interface(self.inputs, None)


class _MemberAssignBody:
    def cpp_body(self) -> str:
        return f"""{self.operand} = {self.value};"""


class _ReturnBody:
    def cpp_body(self) -> str:
        return f"""return {self.value};"""


_include()

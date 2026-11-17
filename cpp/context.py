# lira-simgen-lib/cpp/context.py

from typing import Dict, List, Optional

from lib.interface import InterfacesRegistry
from lib.operand import Variable

from cpp.types import OperandType


def serves(ctx: "Context"):
    def register(name: str, cls: type) -> type:
        ctx._bindings[name] = cls
        InterfacesRegistry.registry[name] = cls
        return cls

    return register


class Context:
    M_CTX = "ctx"

    def __init__(
        self,
        name: str,
        _type: str = None,
        param: str = M_CTX,
        dyn_consts: Optional[Dict[str, Variable]] = None,
    ):
        self.name = name
        self._type = _type
        self._param = param
        self._dyn_consts = dyn_consts or {}
        self._bindings: Dict[str, object] = {}

    def __getattr__(self, member_name):
        member = self._dyn_consts.get(member_name)
        if member is not None:
            return member
        binding = self._bindings.get(member_name)
        if binding is not None:
            return self._invoke(binding)
        raise AttributeError(member_name)

    def _invoke(self, binding):
        def invoke(inputs, out=None):
            return f"{self.name}.{binding(inputs, out)}"

        return invoke

    def bind(self, env_funcs, env_type) -> None:
        for env_func in env_funcs:
            if isinstance(env_func, env_type):
                self._bindings[env_func.name] = env_func

    @property
    def fields(self) -> List[Variable]:
        return list(self._dyn_consts.values())

    def initializer(self, **values: int) -> str:
        unknown = sorted(set(values) - {field.name for field in self.fields})
        if unknown:
            raise ValueError(f"unknown context fields: {unknown}")

        missing = [field.name for field in self.fields if field.name not in values]
        if missing:
            raise ValueError(f"missing context fields: {missing}")

        fields = ", ".join(
            f".{field.name} = {values[field.name]}" for field in self.fields
        )
        return f"{self.name}{{{fields}}}"

    @property
    def param(self) -> str:
        return f"const {self.name}& {self._param}"

    @property
    def declaration(self) -> str:
        members = "\n".join(self._member(field) for field in self.fields)
        return f"""struct {self.name} {{
{members}
}};
"""

    @staticmethod
    def _member(field) -> str:
        if not isinstance(field, Variable):
            raise TypeError(f"unexpected context field: {field!r}")
        if field._type is not None:
            ctype = field._type
        elif field.width is not None:
            ctype = OperandType.gen(field.width)
        else:
            raise ValueError(f"context field '{field.name}' has neither type nor width")
        return f"{ctype} {field.name};"

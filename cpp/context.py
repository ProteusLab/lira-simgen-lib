# lira-simgen-lib/cpp/context.py
# Consumer context: typed members, struct declaration, statement handlers.

from typing import Callable, Dict, List, Optional

from lib.interface import Interface
from lib.operand import Variable

from cpp.types import OperandType


class BaseContext:
    struct_name: Optional[str] = None
    parameter_name = "ctx"

    def __getattr__(self, name: str) -> str:
        if any(field.name == name for field in self.fields):
            return f"{self.parameter_name}.{name}"
        raise AttributeError(name)

    def initializer(self, **values: str) -> str:
        names = [member.name for member in self.fields]
        unknown = sorted(set(values) - set(names))
        if unknown:
            raise ValueError(f"unknown context fields: {unknown}")
        members = ", ".join(
            f".{name} = {values[name]}" for name in names if name in values
        )
        return f"{self.struct_name}{{{members}}}"

    def assign(self, node, *expressions: str) -> str:
        return f"{OperandType.gen(node.shape)} {node.out} = {expressions[0]};"

    def handler(self, key):
        handlers = self.__class__._statement_handlers
        return handlers.get(key) or handlers.get((key[0], None))

    @property
    def fields(self) -> List[Variable]:
        return self.__class__._context_fields

    @property
    def interfaces(self) -> Dict[str, Interface]:
        return self.__class__._context_interfaces

    @property
    def param(self) -> str:
        return f"const {self.struct_name}& {self.parameter_name}"

    @property
    def declaration(self) -> str:
        members = "\n".join(
            f"{OperandType.gen(member.width)} {member.name};" for member in self.fields
        )
        return f"""struct {self.struct_name} {{
{members}
}};
"""


def context(name: str) -> Callable:
    def decorate(cls) -> type:
        fields: Dict[str, Variable] = {}
        interfaces: Dict[str, Interface] = {}
        handlers: Dict[tuple, Callable] = {}
        for base in reversed(cls.__mro__):
            if base is not BaseContext and issubclass(base, BaseContext):
                for field in getattr(base, "_context_fields", []):
                    fields[field.name] = field
                interfaces.update(getattr(base, "_context_interfaces", {}))
                handlers.update(getattr(base, "_statement_handlers", {}))
                for key, value in vars(base).items():
                    if key.startswith("_") or key == "parameter_name":
                        continue
                    if isinstance(value, Variable):
                        fields[value.name] = value
                    elif isinstance(value, Interface):
                        interfaces[key] = value
                    elif callable(value) and hasattr(value, "_statement_key"):
                        handlers[value._statement_key] = value
        cls._context_fields = list(fields.values())
        cls._context_interfaces = interfaces
        cls._statement_handlers = handlers
        cls.struct_name = name

        for key in [
            k for k, v in vars(cls).items() if isinstance(v, (Variable, Interface))
        ]:
            delattr(cls, key)
        return cls

    return decorate


def emit(kind, specifier=None) -> Callable:
    def decorate(method) -> type:
        method._statement_key = getattr(kind, "kind", kind), specifier
        return method

    return decorate

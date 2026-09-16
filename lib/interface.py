# lira-simgen-lib/lib/interface.py

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Iterator, List, Optional

from lira.arch import Arch, EnvironmentFunction

from lib.cpp.func import Func


class Interface(ABC):
    has_mem: ClassVar[bool] = False

    def __init__(self, func: EnvironmentFunction, **linked):
        self.func: EnvironmentFunction = func
        self.attributes: Dict[str, object] = dict(linked)

    @property
    def name(self) -> str:
        return self.func.name

    @property
    def inputs(self) -> List[int]:
        return self.func.inputs

    @property
    def outputs(self) -> List[int]:
        return self.func.outputs

    @abstractmethod
    def __call__(self, inputs: List[str], out: Optional[str] = None) -> str:
        pass

    @property
    def declaration(self) -> str:
        return Func.from_env(self.func).declaration

    @property
    @abstractmethod
    def definition(self) -> str:
        pass


def serves(name: str):
    def decorator(interface_cls):
        InterfacesRegistry.registry[name] = interface_cls
        return interface_cls

    return decorator


class NonImplemented(Interface):
    def __call__(self, inputs: List[str], out: Optional[str] = None) -> str:
        return "// Non Implemented"

    @property
    def definition(self) -> str:
        return ""


class CpuInterface(Interface):
    """Interface served by the CPU state object."""


class MemInterface(Interface):
    """Interface served by memory, independent of the CPU model."""

    has_mem: ClassVar[bool] = True


class InterfacesRegistry:
    registry: ClassVar[Dict[str, type]] = {}

    def __init__(self):
        self._map: Dict[str, Interface] = {}

    @classmethod
    def from_arch(
        cls, arch: Arch, objects: Optional[Dict[str, object]] = None
    ) -> "InterfacesRegistry":
        reg = cls()
        for func in arch.environment_functions:
            attributes = (
                list(func.attributes)
                if isinstance(func.attributes, (list, tuple))
                else [func.attributes]
            )
            interface_cls = cls.registry.get(func.name)
            if interface_cls is not None:
                kwargs = {}
                if objects:
                    for attr in attributes:
                        obj = objects.get(attr)
                        if obj is not None:
                            kwargs[attr] = obj
                reg._map[func.name] = interface_cls(func, **kwargs)
            else:
                print(
                    f"warning: no interface registered for env function "
                    f"'{func.name}'; falling back to 'NonImplemented'"
                )
                reg._map[func.name] = NonImplemented(func)
        for name in cls.registry:
            if name not in reg._map:
                print(
                    f"warning: interface '{name}' is registered but not "
                    f"present in the IR environment functions"
                )
        return reg

    def __iter__(self) -> Iterator[Interface]:
        return iter(self._map.values())

    def __getitem__(self, name: str) -> Interface:
        interface = self._map.get(name)
        assert interface is not None, f"env function '{name}' is not mapped"
        return interface

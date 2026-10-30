# lira-simgen-lib/lib/interface.py

import logging
from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Iterator, List, Optional

from lira.arch import Arch, EnvironmentFunction

from lib.registry import serves as registry_serves

logger = logging.getLogger(__name__)


class Interface(ABC):
    def __init__(self, func: EnvironmentFunction, **linked):
        self.func: EnvironmentFunction = func
        self.attributes: Dict[str, object] = dict(linked)

    @property
    def is_terminator(self) -> bool:
        return False

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


class NonImplemented(Interface):
    def __call__(self, inputs: List[str], out: Optional[str] = None) -> str:
        return "// Non Implemented"


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
                logger.warning(
                    "no interface registered for env function '%s'; falling back to 'NonImplemented'",
                    func.name,
                )
                reg._map[func.name] = NonImplemented(func)

        for name in cls.registry:
            if name not in reg._map:
                logger.warning(
                    "interface '%s' is registered but not present in the IR environment functions",
                    name,
                )
        return reg

    def __iter__(self) -> Iterator[Interface]:
        return iter(self._map.values())

    def __getitem__(self, name: str) -> Interface:
        interface = self._map.get(name)
        assert interface is not None, f"env function '{name}' is not mapped"
        return interface


serves = registry_serves(InterfacesRegistry.registry)

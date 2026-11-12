# lira-simgen-lib/cpp/emitter.py
# Common base class for C++-code emitters.

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Iterable, Optional

from cpp.context import Context
from cpp.func import Func
from lib.templates import Templates


class BaseEmitter(ABC):
    def __init__(self, driver, templates_dir: Path):
        self._driver = driver
        self._templates = Templates(templates_dir)

    @abstractmethod
    def artifacts(self) -> Dict[Path, str]: ...

    def snippet_func(self, name: str) -> Func:
        index = self._driver.index
        return Func.from_snippet(snippet=index.snippet[name], index=index)

    def snippet_funcs(self, names: Iterable[str]) -> Dict[str, Func]:
        return {name: self.snippet_func(name) for name in dict.fromkeys(names)}

    @staticmethod
    def snippet_ctx(snippet, name: str) -> Optional[Context]:
        fields = Func.dyn_fields(snippet)
        return Context(name=name, fields=fields) if fields else None

# lira-simgen-lib/cpp/emitter.py
# Common base class for C++-code emitters.

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

from cpp.context import Context
from cpp.func import Func
from lib.templates import Templates


class BaseEmitter(ABC):
    def __init__(self, driver, templates_dir: Path):
        self._driver = driver
        self._templates = Templates(templates_dir)

    @abstractmethod
    def artifacts(self) -> Dict[Path, str]: ...

    @staticmethod
    def snippet_ctx(snippet, name: str) -> Optional[Context]:
        fields = Func.dyn_fields(snippet)
        return Context(name=name, fields=fields) if fields else None

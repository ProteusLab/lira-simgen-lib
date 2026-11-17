# lira-simgen-lib/cpp/emitter.py
# Common base class for C++-code emitters.

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

from lib.templates import Templates


class BaseEmitter(ABC):
    def __init__(self, driver, templates_dir: Path):
        self._driver = driver
        self._templates = Templates(templates_dir)

    @abstractmethod
    def artifacts(self) -> Dict[Path, str]: ...

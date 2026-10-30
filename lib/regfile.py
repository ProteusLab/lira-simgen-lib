# lira-simgen-lib/lib/regfile.py

import logging
from abc import ABC
from typing import ClassVar, Dict, Optional

from lira.arch import Arch, RegisterFile

from lib.registry import serves as registry_serves

logger = logging.getLogger(__name__)


class IRegFile(ABC):
    def __init__(self, rf: Optional[RegisterFile] = None):
        self.rf: Optional[RegisterFile] = rf

    def register(self, reg) -> object:
        return reg


class RegFileRegistry:
    registry: ClassVar[Dict[str, type]] = {}

    def __init__(self):
        self.reg_files: Dict[str, IRegFile] = {}

    @classmethod
    def from_arch(cls, arch: Arch) -> "RegFileRegistry":
        reg = cls()

        for rf in arch.register_files:
            model_cls = cls.registry.get(rf.name)
            if model_cls is None:
                raise ValueError(f"no register-file model registered for '{rf.name}'")
            reg.reg_files[rf.name] = model_cls(rf)

        for name in cls.registry:
            if name not in reg.reg_files:
                logger.warning(
                    "register-file model '%s' is registered but not present in the IR register files",
                    name,
                )
        return reg


serves = registry_serves(RegFileRegistry.registry)

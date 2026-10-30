# lira-simgen-lib/lib/target.py
# Target-model loading shared by the code generators.

import importlib
from types import ModuleType
from typing import Dict


def import_target_modules(arch_target: str) -> Dict[str, ModuleType]:
    """Import the target-specific models declared by the target package"""
    package = importlib.import_module(f"interpreter.Target.{arch_target}")
    manifest = getattr(package, "MODULES", None)
    if not manifest:
        raise ValueError(
            f"interpreter.Target.{arch_target} does not declare a MODULES manifest"
        )
    return dict(manifest)

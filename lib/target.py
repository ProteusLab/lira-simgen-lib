# lira-simgen-lib/lib/target.py
# Target-model loading shared by the code generators.

import importlib


def import_target_modules(arch_target: str) -> None:
    """Import the target package; its side effects register the target models."""
    importlib.import_module(f"lib.Target.{arch_target}")

# lira-simgen-lib/interpreter/Target/__init__.py

import importlib
from dataclasses import dataclass


@dataclass
class TargetInfo:
    """Target-specific knobs of the generated interpreter."""

    # C++ type of guest addresses (isa::Addr)
    addr_type: str = "uint32_t"
    # Extra members pasted into the generated `CPU` class
    cpu_members: str = ""


def load(name: str) -> TargetInfo:
    """Import `interpreter.Target.<name>`: registers its register-file models,
    interfaces and operation overrides, and returns its `TARGET` info."""
    module = importlib.import_module(f"interpreter.Target.{name}")
    return getattr(module, "TARGET", TargetInfo())

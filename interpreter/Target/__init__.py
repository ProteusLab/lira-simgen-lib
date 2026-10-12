# lira-simgen-lib/interpreter/Target/__init__.py

import importlib
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class TargetInfo:
    """Target-specific knobs of the generated interpreter."""

    # C++ type of guest addresses (isa::Addr)
    addr_type: str = "uint32_t"
    # Extra members pasted into the generated `CPU` class
    cpu_members: str = ""
    # Scalable shapes: lanes_mult -> (C++ expression of the multiplier at run
    # time, `cpu` being the CPU state; its largest value)
    lane_multipliers: Dict[str, Tuple[str, int]] = field(default_factory=dict)


def load(name: str) -> TargetInfo:
    """Import `interpreter.Target.<name>`: registers its register-file models,
    interfaces and operation overrides, and returns its `TARGET` info."""
    module = importlib.import_module(f"interpreter.Target.{name}")
    return getattr(module, "TARGET", TargetInfo())

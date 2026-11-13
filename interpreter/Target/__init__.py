import importlib
from dataclasses import dataclass, field


@dataclass
class TargetInfo:
    """Target-specific storage and interface models for the interpreter."""

    cpu_members: str = ""
    optional_cpu_members: dict = field(default_factory=dict)
    lane_multipliers: dict = field(default_factory=dict)
    register_models: dict = field(default_factory=dict)
    environment_models: dict = field(default_factory=dict)
    runtime_functions: dict = field(default_factory=dict)


def load(name: str) -> TargetInfo:
    module_name = f"interpreter.Target.{name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        return TargetInfo()
    return module.TARGET

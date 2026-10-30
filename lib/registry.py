# lira-simgen-lib/lib/registry.py

from typing import Any, Callable, Dict


def serves(registry: Dict[str, Any]) -> Callable[[str], Callable[[Any], Any]]:
    def by_name(name: str):
        def decorator(cls):
            registry[name] = cls
            return cls

        return decorator

    return by_name

# lira-simgen-lib/interpreter/Target/RISC_V/templates.py

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
)


def render(name: str, **ctx) -> str:
    return _env.get_template(name).render(**ctx)

# lira-simgen-lib/interpreter/templates.py
# jinja2 rendering of the C++ artifact templates.

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class Templates:
    def __init__(self, directory: Path):
        self._env = Environment(
            loader=FileSystemLoader(directory),
            keep_trailing_newline=True,
        )

    def render(self, name: Path, **ctx) -> str:
        return self._env.get_template(str(name)).render(**ctx)

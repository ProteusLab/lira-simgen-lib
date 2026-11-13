from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render(directory: Path, template: str, **values) -> str:
    environment = Environment(
        loader=FileSystemLoader(directory / "templates"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    return environment.get_template(template).render(**values)

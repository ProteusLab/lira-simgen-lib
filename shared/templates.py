from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render(template_dir: Path, template: str, **values) -> str:
    environment = Environment(
        loader=FileSystemLoader(template_dir),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    return environment.get_template(template).render(**values)

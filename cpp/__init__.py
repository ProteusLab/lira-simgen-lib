from pathlib import Path

from lib.templates import Templates

_templates = Templates(Path(__file__).parent / "templates")


def render(name, **ctx):
    return _templates.render(Path(name), **ctx)

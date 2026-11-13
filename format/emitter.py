from pathlib import Path
from typing import Dict

from cpp.emitter import BaseEmitter
from cpp.isa import IsaEmitter


class FormatterEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        self._isa = IsaEmitter(driver)

    def artifacts(self) -> Dict[Path, str]:
        return {
            **self._isa.artifacts(),
            Path("formatter.hh"): self._templates.render(name=Path("formatter.hh.jinja")),
            Path("formatter.cc"): self._templates.render(name=Path("formatter.cc.jinja")),
        }

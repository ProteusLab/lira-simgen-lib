# lira-simgen-lib/lib/config.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict


class IConfig(ABC):
    @abstractmethod
    def artifacts(self, driver) -> Dict[Path, str]:
        pass

    def emit(self, driver, out_dir: Path) -> None:
        for path, content in self.artifacts(driver).items():
            out_path = out_dir / path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w") as out:
                print(content, file=out, end="")

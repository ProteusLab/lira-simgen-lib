# lira-simgen-lib/lib/config.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Dict, Optional, Set, Tuple

from lib.operand import Variable


class IConfig(ABC):
    mach_inst: ClassVar[Variable] = Variable(name="machInst", width=32)

    @property
    def supported_instructions(self) -> Optional[Set[str]]:
        return None

    @property
    @abstractmethod
    def excluded_instructions(self) -> Set[str]:
        pass

    @property
    @abstractmethod
    def decoder_hh(self) -> Path:
        pass

    @property
    @abstractmethod
    def decoder_cc(self) -> Path:
        pass

    @property
    @abstractmethod
    def base_ops_hh(self) -> Path:
        pass

    @property
    @abstractmethod
    def base_ops_cc(self) -> Path:
        pass

    @property
    @abstractmethod
    def snippets_hh(self) -> Path:
        pass

    @property
    @abstractmethod
    def snippets_cc(self) -> Path:
        pass

    @abstractmethod
    def emit_decoder(self, index, insts) -> Tuple[str, str]:
        pass

    @abstractmethod
    def emit_base_ops(self, operations) -> Tuple[str, str]:
        pass

    @abstractmethod
    def emit_snippets(self, driver) -> Tuple[str, str]:
        pass

    def artifacts(self, driver) -> Dict[Path, str]:
        dec_hh, dec_cc = self.emit_decoder(driver.index, driver.insts)
        ops_hh, ops_cc = self.emit_base_ops(driver.arch.operations)
        snp_hh, snp_cc = self.emit_snippets(driver)
        return {
            self.decoder_hh: dec_hh,
            self.decoder_cc: dec_cc,
            self.base_ops_hh: ops_hh,
            self.base_ops_cc: ops_cc,
            self.snippets_hh: snp_hh,
            self.snippets_cc: snp_cc,
        }

    def emit(self, driver, out_dir: Path) -> None:
        for path, content in self.artifacts(driver).items():
            out_path = out_dir / path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w") as out:
                print(content, file=out, end="")

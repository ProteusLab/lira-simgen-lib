# lira-simgen-lib/encoder/config.py

from pathlib import Path
from typing import Dict

from lib.config import IConfig
from lib.templates import Templates

from encoder.emitter import EncoderEmitter


class EncoderConfig(IConfig):
    def __init__(self, arch_target: str):
        self.arch_target = arch_target
        self.templates = Templates(self.templates_dir)
        self.emitter = EncoderEmitter(self)

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "templates"

    @property
    def isa_hh(self) -> Path:
        return Path("isa.hh")

    @property
    def encoder_hh(self) -> Path:
        return Path("encoder.hh")

    @property
    def encoder_cc(self) -> Path:
        return Path("encoder.cc")

    def artifacts(self, driver) -> Dict[Path, str]:
        isa_hh, enc_hh, enc_cc = self.emitter.emit(driver.index, driver.insts)
        return {
            self.isa_hh: isa_hh,
            self.encoder_hh: enc_hh,
            self.encoder_cc: enc_cc,
        }

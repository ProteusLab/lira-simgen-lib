# lira-simgen-lib/decoder/config.py

from pathlib import Path
from typing import Dict

from lib.config import IConfig
from lib.templates import Templates

from decoder.emitter import DecoderEmitter


class DecoderConfig(IConfig):
    def __init__(self, arch_target: str):
        self.arch_target = arch_target
        self.templates = Templates(self.templates_dir)
        self.emitter = DecoderEmitter(self)

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "templates"

    @property
    def isa_hh(self) -> Path:
        return Path("isa.hh")

    @property
    def decoder_hh(self) -> Path:
        return Path("decoder.hh")

    @property
    def decoder_cc(self) -> Path:
        return Path("decoder.cc")

    def artifacts(self, driver) -> Dict[Path, str]:
        dec_hh, dec_cc = self.emitter.decoder(driver.insts)
        isa_hh = self.emitter.isa(driver.insts)
        return {
            self.isa_hh: isa_hh,
            self.decoder_hh: dec_hh,
            self.decoder_cc: dec_cc,
        }

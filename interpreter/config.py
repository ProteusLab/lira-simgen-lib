# lira-simgen-lib/interpreter/config.py

from pathlib import Path
from typing import Dict, Set, Tuple

from lib.config import IConfig

from interpreter.emitter import InterpEmitter
from interpreter.templates import Templates


class SimpleInterpConfig(IConfig):
    CPU_VAR = "cpu"
    MEM_VAR = "mem"

    def __init__(self):
        self.templates = Templates(self.templates_dir)
        self.emitter = InterpEmitter(self)

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "templates"

    @property
    def excluded_instructions(self) -> Set[str]:
        return set()

    @property
    def decoder_hh(self) -> Path:
        return Path("decoder.hh")

    @property
    def decoder_cc(self) -> Path:
        return Path("decoder.cc")

    @property
    def base_ops_hh(self) -> Path:
        return Path("base_ops.hh")

    @property
    def base_ops_cc(self) -> Path:
        return Path("base_ops.cc")

    @property
    def snippets_hh(self) -> Path:
        return Path("snippets.hh")

    @property
    def snippets_cc(self) -> Path:
        return Path("snippets.cc")

    @property
    def isa_hh(self) -> Path:
        return Path("isa.hh")

    @property
    def cpu_state_hh(self) -> Path:
        return Path("cpu_state.hh")

    @property
    def cpu_state_cc(self) -> Path:
        return Path("cpu_state.cc")

    @property
    def interpreter_hh(self) -> Path:
        return Path("naive_interpreter.hh")

    @property
    def interpreter_cc(self) -> Path:
        return Path("naive_interpreter.cc")

    @property
    def isa_hh_jinja(self) -> Path:
        return Path(f"{self.isa_hh}.jinja")

    @property
    def decoder_hh_jinja(self) -> Path:
        return Path(f"{self.decoder_hh}.jinja")

    @property
    def decoder_cc_jinja(self) -> Path:
        return Path(f"{self.decoder_cc}.jinja")

    @property
    def interpreter_hh_jinja(self) -> Path:
        return Path(f"{self.interpreter_hh}.jinja")

    @property
    def interpreter_cc_jinja(self) -> Path:
        return Path(f"{self.interpreter_cc}.jinja")

    @property
    def snippets_hh_jinja(self) -> Path:
        return Path(f"{self.snippets_hh}.jinja")

    @property
    def snippets_cc_jinja(self) -> Path:
        return Path(f"{self.snippets_cc}.jinja")

    @property
    def base_ops_hh_jinja(self) -> Path:
        return Path(f"{self.base_ops_hh}.jinja")

    @property
    def base_ops_cc_jinja(self) -> Path:
        return Path(f"{self.base_ops_cc}.jinja")

    @property
    def cpu_state_hh_jinja(self) -> Path:
        return Path(f"{self.cpu_state_hh}.jinja")

    @property
    def cpu_state_cc_jinja(self) -> Path:
        return Path(f"{self.cpu_state_cc}.jinja")

    def emit_decoder(self, index, insts) -> Tuple[str, str]:
        return self.emitter.decoder(index, insts)

    def emit_base_ops(self, operations) -> Tuple[str, str]:
        return self.emitter.base_ops(operations)

    def emit_snippets(self, driver) -> Tuple[str, str]:
        return self.emitter.snippets(driver.snippet_funcs)

    def artifacts(self, driver) -> Dict[Path, str]:
        artifacts = super().artifacts(driver)
        interp_hh, interp_cc = self.emitter.interpreter(driver.insts)
        cpu_hh, cpu_cc = self.emitter.cpu_state(
            driver.arch, driver.interfaces, driver.reg_files
        )
        artifacts.update(
            {
                self.isa_hh: self.emitter.isa(driver.insts),
                self.cpu_state_hh: cpu_hh,
                self.cpu_state_cc: cpu_cc,
                self.interpreter_hh: interp_hh,
                self.interpreter_cc: interp_cc,
            }
        )
        return artifacts

# lira-simgen-lib/interpreter/config.py

from pathlib import Path
from typing import Dict, Tuple

from lib.config import IConfig
from lib.templates import Templates

from interpreter.emitter import InterpEmitter


class SimpleInterpConfig(IConfig):
    M_CPU = "m_cpu"
    M_MEM = "m_mem"

    def __init__(self, arch_target: str):
        self.arch_target = arch_target
        self.templates = Templates(self.templates_dir)
        self.emitter = InterpEmitter(self)

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "templates"

    @property
    def cpu_state_hh(self) -> Path:
        return Path("cpu_state.hh")

    @property
    def cpu_state_cc(self) -> Path:
        return Path("cpu_state.cc")

    @property
    def execute_hh(self) -> Path:
        return Path("execute.hh")

    @property
    def execute_cc(self) -> Path:
        return Path("execute.cc")

    def artifacts(self, driver) -> Dict[Path, str]:
        exec_hh, exec_cc = self.emitter.execute(driver.insts)
        cpu_hh, cpu_cc = self.emitter.cpu_state(
            driver.arch, driver.interfaces, driver.reg_files
        )
        return {
            self.execute_hh: exec_hh,
            self.execute_cc: exec_cc,
            self.cpu_state_hh: cpu_hh,
            self.cpu_state_cc: cpu_cc,
        }

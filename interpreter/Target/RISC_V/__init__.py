from interpreter.Target import TargetInfo
from interpreter.Target.RISC_V.interface import INTERFACES
from interpreter.Target.RISC_V.regfile import REGISTER_FILES


TARGET = TargetInfo(
    register_models=REGISTER_FILES,
    environment_models=INTERFACES,
    runtime_functions={"sysCall": ((), ())},
)

from interpreter.interface import CpuInterface, PcFunction, read_mem, write_mem


INTERFACES = {
    **{f"readMem{width}": read_mem for width in (8, 16, 32)},
    **{f"writeMem{width}": write_mem for width in (8, 16, 32)},
    "getPC": lambda _, **linked: PcFunction("getPC"),
    "setPC": lambda _, **linked: PcFunction("setPC"),
    "sysCall": CpuInterface,
}

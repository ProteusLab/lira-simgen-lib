"""AArch64 bindings to the generated CPU and memory."""

from functools import partial

from interpreter.interface import CpuInterface, PcFunction, read_mem, read_mem_no_fault, write_mem


# Keep runtime methods available when generating from a subset of the ISA.
RUNTIME_FUNCTIONS = {
    "supervisor_call": ((16,), ()),
    "mem_copy": ((64, 64, 64, 1), ()),
    "mem_set": ((64, 64, 8), ()),
    "check_alignment": ((64, 8, 1), ()),
    "exclusive_mark": ((64, 8), ()),
    "exclusive_check": ((64, 8), (1,)),
    "exclusive_clear": ((), ()),
    "pac_add": ((64, 64, 3), (64,)),
    "pac_auth": ((64, 64, 3), (64,)),
    "pac_strip": ((64, 1), (64,)),
    "pac_generic": ((64, 64), (64,)),
    "barrier": ((4, 4), ()),
    "hint": ((7,), ()),
    "wait_timeout": ((1, 64), ()),
    "branch_target": ((2,), ()),
    "exception_call": ((3, 16), ()),
    "exception_return": ((2,), ()),
    "debug_state": ((2,), ()),
    "sys_op": ((3, 4, 4, 3, 64), ()),
    "sys_op_read": ((3, 4, 4, 3), (64,)),
    "sysreg_read": ((1, 3, 4, 4, 3), (64,)),
    "sysreg_write": ((1, 3, 4, 4, 3, 64), ()),
    "pstate_write": ((3, 3, 4), ()),
    "sme_access_trap": ((3,), ()),
}

INTERFACES = {
    "pc_read": lambda _: PcFunction("getPC"),
    "pc_write": lambda _: PcFunction("setPC"),
    **{f"mem_read_{width}": read_mem for width in (8, 16, 32, 64, 128)},
    **{f"mem_write_{width}": write_mem for width in (8, 16, 32, 64, 128)},
    **{f"mem_read_nf_{width}": read_mem_no_fault for width in (8, 16, 32, 64)},
    **{
        name: partial(CpuInterface, takes_memory=True)
        for name in ("supervisor_call", "mem_copy", "mem_set", "sys_op")
    },
}

# Shared state and helpers for the native Protea IR (PIR) -> LIRA IR converter

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from lira.arch import EnvironmentFunction, RegisterFile
from lira.ir_builder import ArchBuilder, BaseBuilder

from lib.attributes import PC_ATTRIBUTE
from lib.snippet import SnippetKind


def width_of(ir_type):
    match = re.match(r"[busr](\d+)$", ir_type)
    return int(match.group(1)) if match else 32


def is_signed(ir_type):
    return ir_type.startswith("s")


def is_unsigned(ir_type):
    return ir_type.startswith("u")


@dataclass
class Context:
    """State shared by every snippet/semantic session of one architecture."""

    builder: ArchBuilder
    reg_files: Dict[str, RegisterFile]  # register-file name -> register file
    pc_regs: Set[str]  # register names marked with the PC attribute
    envs: List[EnvironmentFunction]
    get_pc: EnvironmentFunction
    set_pc: EnvironmentFunction
    used: Dict[str, object] = field(default_factory=dict)  # op name -> instance
    counters: Dict[SnippetKind, int] = field(
        default_factory=lambda: {kind: 0 for kind in SnippetKind}
    )

    def add_snippet(self, snippet, kind: SnippetKind) -> str:
        number = self.counters[kind]
        self.counters[kind] = number + 1
        snippet.name = f"{kind.value}_{number}"
        self.builder.add_snippet(snippet)
        return snippet.name


@dataclass
class Scope:
    ctx: Context
    seq: BaseBuilder
    vars: Dict[str, object] = field(default_factory=dict)  # name -> Value | width
    operand_names: tuple[str, ...] = ()
    fields: Dict[str, object] = field(default_factory=dict)  # field name -> field
    raw: Optional[object] = None  # decode input value


def find_env(ctx: Context, name, inputs, outputs):
    for env in ctx.envs:
        if env.name == name and list(env.inputs) == inputs and list(env.outputs) == outputs:
            return env
    raise ValueError(
        f"no environment function '{name}' with inputs {inputs} and outputs {outputs}"
    )

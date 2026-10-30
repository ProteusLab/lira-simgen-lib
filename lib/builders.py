# lira-simgen-lib/simgen/builders.py

from abc import ABC, ABCMeta, abstractmethod
from typing import Dict, List, Optional, cast

from lira.arch import Instruction as LiraInstruction
from lira.arch_utils import ArchIndex
from lira.ir import Statement, StatementSeq
from lira.ir_std import (
    CondEnv,
    StmtConst,
    StmtDynConst,
    StmtEnv,
    StmtInput,
    StmtOp,
    StmtOutput,
    StmtRead,
    StmtWrite,
)

from lib.config import IConfig
from lib.nodes import (
    EnvExec,
    Input,
    Op,
    ReadMem,
    ReadReg,
    Return,
    WriteReg,
)


from lib.operand import Constant, Register, Variable


class IBuilder(ABC):
    @abstractmethod
    def build(self, seq: StatementSeq) -> List[object]:
        pass


class StmtHandler(ABC):
    def __init__(self, builder: IBuilder, stmt: Statement):
        self.builder: IBuilder = builder
        self.stmt: Statement = stmt

    @abstractmethod
    def build(self) -> None:
        pass


def serves(kind: str):
    def decorator(handler_cls):
        assert issubclass(handler_cls, StmtHandler)
        handler_cls.handler_kind = kind
        return handler_cls

    return decorator


class BuilderMeta(ABCMeta):
    def __new__(mcls, name, bases, ns):
        cls = super().__new__(mcls, name, bases, ns)
        handlers = {}
        for base in reversed(cls.__mro__):
            handlers.update(getattr(base, "handlers", {}))
        for value in ns.values():
            kind = getattr(value, "handler_kind", None)
            if kind is not None:
                handlers[kind] = value
        cls.handlers = handlers
        return cls


class CodeBuilder(IBuilder, metaclass=BuilderMeta):
    handlers: Dict[str, type]

    def __init__(
        self,
        index: ArchIndex,
        mach_inst: Optional[Variable] = None,
        params: Optional[List[Variable]] = None,
    ):
        self.index: ArchIndex = index
        self.mach_inst: Variable = (
            mach_inst if mach_inst is not None else IConfig.mach_inst
        )
        self.params: List[Variable] = params if params is not None else [self.mach_inst]
        self.nodes: List[object] = []
        self._vars: Dict[str, Variable] = {}
        self.ret: Optional[Variable] = None

    def _dispatch(self, stmt: Statement) -> None:
        handler_cls = type(self).handlers.get(stmt.kind)
        if handler_cls is None:
            raise ValueError(f"Unsupported statement kind '{stmt.kind}'")
        handler_cls(self, stmt).build()

    def build(self, seq: StatementSeq) -> List[object]:
        for stmt in seq.stmts:
            self._dispatch(stmt)
        return self.nodes

    def variable(self, name: str, width: int) -> Variable:
        if name in self._vars:
            return self._vars[name]
        var = Variable(name, width)
        self._vars[name] = var
        return var

    def resolve_var(self, name: str) -> Variable:
        return self._vars[name]

    @serves(StmtInput.kind)
    class InputHandler(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            out = self.stmt.outputs[0]
            var = builder.variable(out, self.stmt.outputs_types[0])
            idx = int(self.stmt.specifier)
            if idx >= len(builder.params):
                raise ValueError(f"input {idx} is not bound to a parameter")
            builder.nodes.append(Input(var, builder.params[idx]))

    @serves(StmtConst.kind)
    class Const(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            out = self.stmt.outputs[0]
            const = Constant(out, self.stmt.outputs_types[0], self.stmt.specifier)
            builder._vars[out] = const
            builder.nodes.append(const)

    @serves(StmtOp.kind)
    class OpHandler(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            out = self.stmt.outputs[0]
            var = builder.variable(out, self.stmt.outputs_types[0])
            inputs = [builder.resolve_var(a) for a in self.stmt.inputs]
            op = builder.index.op[self.stmt.specifier]
            builder.nodes.append(Op(var, op, inputs))

    @serves(StmtOutput.kind)
    class Output(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            val = builder.resolve_var(self.stmt.inputs[0])
            builder.ret = val
            builder.nodes.append(Return(val))


class SemanticBuilder(CodeBuilder):
    def __init__(self, index: ArchIndex, insn: LiraInstruction, interfaces, reg_files):
        super().__init__(index)
        self.insn: LiraInstruction = insn
        self.interfaces = interfaces
        self.reg_files = reg_files

        self.regs: List[Register] = [
            Register(operand, size, self.index.snippet[snip_name])
            for operand, size, snip_name in zip(
                insn.operand_names, insn.operand_sizes, insn.encoding.decode
            )
        ]
        self._read_count = 0
        self._write_count = 0

    def build(self, seq: StatementSeq) -> List[object]:
        # Producers map: output name -> first statement producing it.
        self.producers: Dict[str, Statement] = {}
        for stmt in seq.stmts:
            for out in stmt.outputs:
                self.producers.setdefault(out, stmt)
            self._dispatch(stmt)
        return self.nodes

    @serves(StmtInput.kind)
    class Noop(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            builder._vars[self.stmt.outputs[0]] = builder.regs[int(self.stmt.specifier)]

    @serves(StmtRead.kind)
    class Read(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            producer = builder.producers[self.stmt.inputs[0]]
            reg = cast(Register, builder.resolve_var(producer.outputs[0]))
            reg.rf = builder.reg_files[self.stmt.specifier]
            if reg.src_pos is None:
                reg.src_pos = builder._read_count
                builder._read_count += 1
            out = self.stmt.outputs[0]
            var = builder.variable(out, self.stmt.outputs_types[0])
            builder.nodes.append(ReadReg(reg, var))

    @serves(StmtWrite.kind)
    class Write(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            producer = builder.producers[self.stmt.inputs[0]]
            reg = cast(Register, builder.resolve_var(producer.outputs[0]))
            reg.rf = builder.reg_files[self.stmt.specifier]
            if reg.dst_pos is None:
                reg.dst_pos = builder._write_count
                builder._write_count += 1
            val = builder.resolve_var(self.stmt.inputs[1])
            builder.nodes.append(WriteReg(reg, val))

    @serves(StmtEnv.kind)
    class Env(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            func = builder.index.env[self.stmt.specifier]
            interface = builder.interfaces[self.stmt.specifier]

            if interface is None:
                raise ValueError(
                    f"{builder.insn.name}: env '{func.name}' is not supported yet"
                )

            inputs = [builder.resolve_var(a) for a in self.stmt.inputs]
            if self.stmt.outputs:
                out = self.stmt.outputs[0]
                width = self.stmt.outputs_types[0]
                data = builder.variable(out, width)
                builder.nodes.append(ReadMem(data, inputs, interface))
            else:
                builder.nodes.append(EnvExec(inputs, interface))

    @serves(CondEnv.kind)
    class CondEnv(StmtHandler):
        def build(self) -> None:
            raise NotImplementedError("'cond_env' statement is not supported yet")

    @serves(StmtDynConst.kind)
    class DynConst(StmtHandler):
        def build(self) -> None:
            raise NotImplementedError("'dyn_const' statement is not supported yet")

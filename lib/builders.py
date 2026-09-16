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
    InputAssign,
    MemberAssign,
    OpAssign,
    ReadMem,
    ReadReg,
    Return,
    WriteReg,
)


from lib.operand import Constant, Operand, Register, Variable


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
        self.params: List[Variable] = (
            params if params is not None else [self.mach_inst]
        )
        self.nodes: List[object] = []
        self._vars: Dict[str, Variable] = {}

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
    class Input(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            out = self.stmt.outputs[0]
            var = builder.variable(out, self.stmt.outputs_types[0])
            idx = int(self.stmt.specifier)
            if idx >= len(builder.params):
                raise ValueError(
                    f"input {idx} is not bound to a parameter"
                )
            builder.nodes.append(InputAssign(var, builder.params[idx]))

    @serves(StmtConst.kind)
    class Const(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            out = self.stmt.outputs[0]
            const = Constant(out, self.stmt.outputs_types[0], self.stmt.specifier)
            builder._vars[out] = const
            builder.nodes.append(const)

    @serves(StmtOp.kind)
    class Op(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            out = self.stmt.outputs[0]
            var = builder.variable(out, self.stmt.outputs_types[0])
            inputs = [builder.resolve_var(a) for a in self.stmt.inputs]
            op = builder.index.op[self.stmt.specifier]
            builder.nodes.append(OpAssign(var, op, inputs))


class SemanticBuilder(CodeBuilder):
    def __init__(self, index: ArchIndex, insn: LiraInstruction, interfaces, reg_files):
        super().__init__(index)
        self.insn: LiraInstruction = insn
        self.interfaces = interfaces
        self.reg_files = reg_files
        self.read_operands: List[str] = []
        self.write_operands: List[str] = []
        self.has_mem: bool = False
        self.regs: List[Register] = []

    def _scan(self) -> None:
        seq = self.insn.semantic
        for stmt in seq.stmts:
            scan_fn = getattr(self, f"_scan_{stmt.kind}", None)
            if scan_fn is not None:
                scan_fn(stmt)

    def _scan_read(self, stmt: Statement) -> None:
        producer = stmt.input(0, self.insn.semantic)
        idx = int(producer.specifier)
        self.read_operands.append(self.insn.operand_names[idx])

    def _scan_write(self, stmt: Statement) -> None:
        producer = stmt.input(0, self.insn.semantic)
        idx = int(producer.specifier)
        self.write_operands.append(self.insn.operand_names[idx])

    def _scan_env(self, stmt: Statement) -> None:
        interface = self.interfaces[stmt.specifier]
        if interface is not None and interface.has_mem:
            self.has_mem = True

    def _build_regs(self) -> None:
        for idx, (operand, snip_name) in enumerate(
            zip(self.insn.operand_names, self.insn.encoding.decode)
        ):
            src_pos = (
                self.read_operands.index(operand)
                if operand in self.read_operands
                else None
            )
            dst_pos = (
                self.write_operands.index(operand)
                if operand in self.write_operands
                else None
            )
            reg = Register(
                operand,
                self.insn.operand_sizes[idx],
                self.index,
                self.index.snippet[snip_name],
                src_pos,
                dst_pos,
            )
            self.regs.append(reg)

        for stmt in self.insn.semantic.stmts:
            if stmt.kind == StmtInput.kind:
                self._vars[stmt.outputs[0]] = self.regs[int(stmt.specifier)]

    def _bind_reg_files(self) -> None:
        for stmt in self.insn.semantic.stmts:
            if stmt.kind not in (StmtRead.kind, StmtWrite.kind):
                continue
            producer = stmt.input(0, self.insn.semantic)
            self.regs[int(producer.specifier)].rf = self.reg_files[stmt.specifier]

    def build(self, seq: StatementSeq) -> List[object]:
        self._scan()
        self._build_regs()
        self._bind_reg_files()
        return super().build(seq)

    @serves(StmtInput.kind)
    class Noop(StmtHandler):
        def build(self) -> None:
            pass

    @serves(StmtRead.kind)
    class Read(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            producer = self.stmt.input(0, builder.insn.semantic)
            reg = cast(Register, builder.resolve_var(producer.outputs[0]))
            out = self.stmt.outputs[0]
            var = builder.variable(out, self.stmt.outputs_types[0])
            builder.nodes.append(ReadReg(reg, var))

    @serves(StmtWrite.kind)
    class Write(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            producer = self.stmt.input(0, builder.insn.semantic)
            reg = cast(Register, builder.resolve_var(producer.outputs[0]))
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
            raise NotImplementedError(
                "'cond_env' statement is not supported yet"
            )

    @serves(StmtDynConst.kind)
    class DynConst(StmtHandler):
        def build(self) -> None:
            raise NotImplementedError(
                "'dyn_const' statement is not supported yet"
            )


class ConstraintBuilder(CodeBuilder):
    def __init__(
        self,
        index: ArchIndex,
        mach_inst: Optional[Variable] = None,
        params: Optional[List[Variable]] = None,
    ):
        super().__init__(index, mach_inst, params)

    @serves(StmtOutput.kind)
    class Output(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            val = builder.resolve_var(self.stmt.inputs[0])
            builder.nodes.append(Return(val))


class DecodeBuilder(CodeBuilder):
    def __init__(
        self,
        index: ArchIndex,
        operand: Operand,
        mach_inst: Optional[Variable] = None,
    ):
        super().__init__(index, mach_inst)
        self.operand: Operand = operand

    @serves(StmtOutput.kind)
    class Output(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            val = builder.resolve_var(self.stmt.inputs[0])
            builder.nodes.append(MemberAssign(builder.operand, val))

# lira-simgen-lib/simgen/builders.py

from abc import ABC, ABCMeta, abstractmethod
from typing import Dict, List, Optional

from lira.arch import Instruction as LiraInstruction
from lira.arch_utils import ArchIndex
from lira.ir import Statement, StatementSeq
from lira.ir_std import (
    CondEnv,
    StmtConst,
    StmtDynConst,
    StmtEnv,
    StmtFop,
    StmtInput,
    StmtOp,
    StmtOutput,
    StmtRead,
    StmtWrite,
)

from lib.config import IConfig
from lib.nodes import (
    LANE_INDEX,
    CondEnv as CondEnvNode,
    ConstDef,
    EnvExec,
    Fold,
    Fop,
    Input,
    LaneLoop,
    Op,
    ReadMem,
    ReadReg,
    ReadRegLanes,
    Return,
    VecCall,
    WriteReg,
    WriteRegLanes,
)


from lib.operand import Constant, LaneView, Register, Variable
from lib.types import OperandType


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
        self._outputs: Dict[int, Variable] = {}

    def _dispatch(self, stmt: Statement) -> None:
        handler_cls = type(self).handlers.get(stmt.kind)
        if handler_cls is None:
            raise ValueError(f"Unsupported statement kind '{stmt.kind}'")
        handler_cls(self, stmt).build()

    def build(self, seq: StatementSeq) -> List[object]:
        for stmt in seq.stmts:
            self._dispatch(stmt)
        if self._outputs:
            self.nodes.append(Return([self._outputs[i] for i in sorted(self._outputs)]))
        return self.nodes

    def variable(self, name: str, width: int, lanes: int = 1) -> Variable:
        if name in self._vars:
            return self._vars[name]
        var = Variable(name, width, lanes)
        self._vars[name] = var
        return var

    def resolve_var(self, name: str) -> Variable:
        return self._vars[name]

    def outputs(self, stmt: Statement) -> List[Variable]:
        """The output variables of a statement, with its shape."""
        return [
            self.variable(name, width, stmt.shape.lanes_base)
            for name, width in zip(stmt.outputs, stmt.outputs_types)
        ]

    def lanewise(self, stmt: Statement, make_node) -> None:
        """Add the node `make_node(outs, inputs)` for a statement that works
        lane by lane: directly for a scalar, in a loop over the lanes of a
        vector."""
        outs = self.outputs(stmt)
        inputs = [self.resolve_var(a) for a in stmt.inputs]
        lanes = stmt.shape.lanes_base
        if lanes == 1:
            self.nodes.append(make_node(outs, inputs))
            return
        view = lambda v: LaneView(v, LANE_INDEX)  # noqa: E731
        body = make_node([view(o) for o in outs], [view(i) for i in inputs])
        self.nodes.append(LaneLoop(outs, lanes, body))

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
            const = Constant(
                out,
                self.stmt.outputs_types[0],
                self.stmt.specifier,
                self.stmt.shape.lanes_base,
            )
            builder._vars[out] = const
            builder.nodes.append(ConstDef(const))

    @serves(StmtOp.kind)
    class OpHandler(StmtHandler):
        def build(self) -> None:
            op = self.builder.index.op[self.stmt.specifier]
            self.builder.lanewise(self.stmt, lambda outs, ins: Op(outs, op, ins))

    class VecHandler(StmtHandler):
        """Vector statement computed by a prot::vec helper."""

        helper: str

        def build(self) -> None:
            builder = self.builder
            out = builder.outputs(self.stmt)[0]
            args = [builder.resolve_var(a) for a in self.stmt.inputs]
            builder.nodes.append(VecCall(out, self.helper, args))

    @serves("index")
    class Index(VecHandler):
        helper = "iota"

    @serves("replicate")
    class Replicate(VecHandler):
        helper = "splat"

    @serves("gather")
    class Gather(VecHandler):
        helper = "gather"

    @serves("extract_first")
    class ExtractFirst(VecHandler):
        helper = "resize"

    @serves("extend_zero")
    class ExtendZeroLanes(VecHandler):
        helper = "resize"

    @serves("fold")
    class FoldHandler(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            if len(self.stmt.outputs) != 1:
                raise NotImplementedError("'fold' with several state values")
            out = builder.variable(self.stmt.outputs[0], self.stmt.outputs_types[0])
            state, *vectors = [builder.resolve_var(a) for a in self.stmt.inputs]
            op = builder.index.op[self.stmt.specifier]
            builder.nodes.append(
                Fold(out, op, state, vectors, self.stmt.shape.lanes_base)
            )

    @serves(StmtOutput.kind)
    class Output(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            val = builder.resolve_var(self.stmt.inputs[0])
            builder._outputs[int(self.stmt.specifier)] = val


class SemanticBuilder(CodeBuilder):
    def __init__(
        self,
        index: ArchIndex,
        insn: LiraInstruction,
        interfaces,
        reg_files,
        fops=None,
        fpu=None,
    ):
        super().__init__(index)
        self.insn: LiraInstruction = insn
        # float operations by name and the FPU model rendering them
        self.fops = fops or {}
        self.fpu = fpu
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

    def _operand_index(self, stmt: Statement) -> Optional[int]:
        """Operand that directly provides the register index of a read/write."""
        producer = stmt.input(0, self.insn.semantic)
        if producer.kind != StmtInput.kind:
            return None
        return int(producer.specifier)

    def _scan_read(self, stmt: Statement) -> None:
        idx = self._operand_index(stmt)
        if idx is not None:
            self.read_operands.append(self.insn.operand_names[idx])

    def _scan_write(self, stmt: Statement) -> None:
        idx = self._operand_index(stmt)
        if idx is not None:
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
            idx = self._operand_index(stmt)
            if idx is not None:
                self.regs[idx].rf = self.reg_files[stmt.specifier]

    def build(self, seq: StatementSeq) -> List[object]:
        self._scan()
        self._build_regs()
        self._bind_reg_files()
        return super().build(seq)

    @serves(StmtInput.kind)
    class Noop(StmtHandler):
        def build(self) -> None:
            pass

    def reg_width(self, rf_name: str) -> int:
        return self.index.rf[rf_name].reg_size.lanes_base

    @serves(StmtRead.kind)
    class Read(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            index = builder.resolve_var(self.stmt.inputs[0])
            var = builder.outputs(self.stmt)[0]
            rf = builder.reg_files[self.stmt.specifier]
            if var.lanes == 1:
                builder.nodes.append(ReadReg(rf, index, var))
                return
            reg_type = OperandType.gen(builder.reg_width(self.stmt.specifier))
            builder.nodes.append(ReadRegLanes(rf, index, var, reg_type, var.width))

    @serves(StmtWrite.kind)
    class Write(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            index = builder.resolve_var(self.stmt.inputs[0])
            val = builder.resolve_var(self.stmt.inputs[1])
            rf = builder.reg_files[self.stmt.specifier]
            lanes = self.stmt.shape.lanes_base
            if lanes == 1:
                builder.nodes.append(WriteReg(rf, index, val))
                return
            width = builder.reg_width(self.stmt.specifier)
            reg_type = OperandType.gen(width)
            builder.nodes.append(WriteRegLanes(rf, index, val, reg_type, width // lanes))

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

            if self.stmt.outputs:
                builder.lanewise(
                    self.stmt, lambda outs, ins: ReadMem(outs[0], ins, interface)
                )
            else:
                builder.lanewise(self.stmt, lambda outs, ins: EnvExec(ins, interface))

    @serves(CondEnv.kind)
    class CondEnv(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            interface = builder.interfaces[self.stmt.specifier]
            if interface.has_mem:
                builder.has_mem = True
            # inputs: cond, env arguments..., on_false values (one per output)
            num_args = len(self.stmt.inputs) - 1 - len(self.stmt.outputs)
            builder.lanewise(
                self.stmt,
                lambda outs, args: CondEnvNode(
                    args[0],
                    args[1 : 1 + num_args],
                    args[1 + num_args :],
                    outs,
                    interface,
                ),
            )

    @serves(StmtFop.kind)
    class FopHandler(StmtHandler):
        def build(self) -> None:
            builder = self.builder
            fop = builder.fops[self.stmt.specifier]
            builder.lanewise(
                self.stmt, lambda outs, ins: Fop(outs, fop, ins, builder.fpu)
            )

    @serves(StmtDynConst.kind)
    class DynConst(StmtHandler):
        def build(self) -> None:
            raise NotImplementedError("'dyn_const' statement is not supported yet")

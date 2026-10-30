# lira-simgen-lib/lib/builders.py

from typing import Dict, List, Optional

from lira.arch import Instruction as LiraInstruction
from lira.arch_utils import ArchIndex
from lira.ir import Shape, Statement, StatementSeq
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

from lib.nodes import DynConst, EnvCall, Input, Op, Output, Raw, ReadReg, WriteReg
from lib.operand import Constant, Register, Variable


class CodeBuilder:
    def __init__(
        self,
        index: ArchIndex,
        inputs: Optional[List[Variable]] = None,
        insn: Optional[LiraInstruction] = None,
        interfaces=None,
        reg_files=None,
    ):
        self.index: ArchIndex = index
        self.inputs: List[Variable] = inputs or []
        self.insn: Optional[LiraInstruction] = insn
        self.interfaces = interfaces
        self.reg_files = reg_files
        self._vars: Dict[str, Variable] = {}
        self.ret: Optional[Variable] = None
        self._read_count = 0
        self._write_count = 0

        if insn is not None:
            self.inputs = [
                Register(operand, size, self.index.snippet[snip_name])
                for operand, size, snip_name in zip(
                    insn.operand_names, insn.operand_sizes, insn.encoding.decode
                )
            ]

    def build(self, seq: StatementSeq) -> List[object]:
        if self.insn is not None:
            self.producers: Dict[str, Statement] = {}
            for stmt in seq.stmts:
                for out in stmt.outputs:
                    self.producers.setdefault(out, stmt)
        return [self._dispatch(stmt) for stmt in seq.stmts]

    def _dispatch(self, stmt: Statement) -> Optional[object]:
        method = getattr(self, f"process_{stmt.kind}", None)
        if method is None:
            for out, width in zip(stmt.outputs, stmt.outputs_types):
                self.variable(out, width)
            node = Raw(stmt)
        else:
            node = method(stmt)
        if node is not None:
            node._stmt_key = (stmt.kind, stmt.specifier)
        return node

    def process_input(self, stmt: StmtInput) -> Input:
        out = stmt.outputs[0]
        var = self.variable(out, stmt.outputs_types[0])
        idx = int(stmt.specifier)
        if idx >= len(self.inputs):
            raise ValueError(f"input {idx} is not bound to a parameter")
        source = self.inputs[idx]
        if isinstance(source, Register):
            self._vars[out] = source
        return Input(var, source)

    def process_const(self, stmt: StmtConst) -> Constant:
        out = stmt.outputs[0]
        const = Constant(out, stmt.outputs_types[0], stmt.specifier)
        self._vars[out] = const
        return const

    def process_op(self, stmt: StmtOp) -> Op:
        out = stmt.outputs[0]
        var = self.variable(out, stmt.outputs_types[0])
        inputs = [self.resolve_var(a) for a in stmt.inputs]
        op = self.index.op[stmt.specifier]
        return Op(var, op, inputs)

    def process_output(self, stmt: StmtOutput) -> Output:
        val = self.resolve_var(stmt.inputs[0])
        self.ret = val
        return Output(val)

    def process_dyn_const(self, stmt: StmtDynConst) -> DynConst:
        out = stmt.outputs[0]
        var = self.variable(out, stmt.outputs_types[0])
        self._vars[out] = var
        return DynConst(var, Shape(stmt.outputs_types[0], None), stmt.specifier)

    def process_read(self, stmt: StmtRead) -> ReadReg:
        producer = self.producers[stmt.inputs[0]]
        reg = self.resolve_var(producer.outputs[0])
        assert isinstance(reg, Register)
        reg.rf = self.reg_files.get(stmt.specifier)
        if reg.src_pos is None:
            reg.src_pos = self._read_count
            self._read_count += 1
        out = stmt.outputs[0]
        var = self.variable(out, stmt.outputs_types[0])
        return ReadReg(reg, var)

    def process_write(self, stmt: StmtWrite) -> WriteReg:
        producer = self.producers[stmt.inputs[0]]
        reg = self.resolve_var(producer.outputs[0])
        assert isinstance(reg, Register)
        reg.rf = self.reg_files.get(stmt.specifier)
        if reg.dst_pos is None:
            reg.dst_pos = self._write_count
            self._write_count += 1
        val = self.resolve_var(stmt.inputs[1])
        return WriteReg(reg, val)

    def process_env(self, stmt: StmtEnv) -> EnvCall:
        func = self.index.env[stmt.specifier]
        interface = self.interfaces[stmt.specifier]

        if interface is None:
            raise ValueError(
                f"{self.insn.name}: env '{func.name}' is not supported yet"
            )

        inputs = [self.resolve_var(a) for a in stmt.inputs]
        out = None
        if stmt.outputs:
            out = self.variable(stmt.outputs[0], stmt.outputs_types[0])
        return EnvCall(inputs, interface, out)

    def process_cond_env(self, stmt: CondEnv) -> None:
        raise NotImplementedError("'cond_env' statement is not supported yet")

    def variable(self, name: str, width: int) -> Variable:
        if name in self._vars:
            return self._vars[name]
        var = Variable(name, width)
        self._vars[name] = var
        return var

    def resolve_var(self, name: str) -> Variable:
        return self._vars[name]

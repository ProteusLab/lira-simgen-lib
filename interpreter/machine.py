"""Minimal reference interpreter for LIRA statement sequences.

Standard operations follow SMT-LIB bit-vector semantics (shifts by >= width give
0 / sign fill, signed division truncates and wraps). A scalable shape `<n>VQ`
has n * vq lanes, `<n>VQVQ` n * vq * vq; `vq` (the SVE vector length in
quadwords) is fixed per machine.
"""

import re
from collections.abc import Callable

from lira.arch import Arch, Instruction, Operation
from lira.ir import StatementSeq


def _bit_mask(width: int) -> int:
    return (1 << width) - 1


def _as_signed(value: int, width: int) -> int:
    return value - (1 << width) if value >> (width - 1) & 1 else value


def _std(base: str, op: Operation, a: list[int]) -> list[int]:
    n = op.inputs[-1]
    o = op.outputs[0]
    if base == "not":
        r = ~a[0]
    elif base == "neg":
        r = -a[0]
    elif base == "popcnt":
        r = a[0].bit_count()
    elif base == "clz":
        r = n - a[0].bit_length()
    elif base == "ctz":
        r = n if a[0] == 0 else (a[0] & -a[0]).bit_length() - 1
    elif base == "reverse":
        r = int(format(a[0], f"0{n}b")[::-1], 2)
    elif base == "add":
        r = a[0] + a[1]
    elif base == "sub":
        r = a[0] - a[1]
    elif base == "mul":
        r = a[0] * a[1]
    elif base == "and":
        r = a[0] & a[1]
    elif base == "orr":
        r = a[0] | a[1]
    elif base == "xor":
        r = a[0] ^ a[1]
    elif base == "lsl":
        r = a[0] << a[1] if a[1] < n else 0
    elif base == "lsr":
        r = a[0] >> a[1] if a[1] < n else 0
    elif base == "asr":
        r = _as_signed(a[0], n) >> min(a[1], n)
    elif base == "ror":
        k = a[1] % n
        r = (a[0] >> k) | (a[0] << (n - k))
    elif base == "rol":
        k = a[1] % n
        r = (a[0] << k) | (a[0] >> (n - k))
    elif base in ("eq", "ne", "slt", "sle", "sgt", "sge", "ult", "ule", "ugt", "uge"):
        x, y = (
            (a[0], a[1])
            if base[0] == "u" or base in ("eq", "ne")
            else (_as_signed(a[0], n), _as_signed(a[1], n))
        )
        r = {
            "eq": x == y,
            "ne": x != y,
            "slt": x < y,
            "sle": x <= y,
            "sgt": x > y,
            "sge": x >= y,
            "ult": x < y,
            "ule": x <= y,
            "ugt": x > y,
            "uge": x >= y,
        }[base]
    elif base == "add_overflow":
        s = _as_signed(a[0], n) + _as_signed(a[1], n)
        r = not (-(1 << (n - 1)) <= s < (1 << (n - 1)))
    elif base == "sub_overflow":
        s = _as_signed(a[0], n) - _as_signed(a[1], n)
        r = not (-(1 << (n - 1)) <= s < (1 << (n - 1)))
    elif base == "div_u":
        r = a[2] if a[1] == 0 else a[0] // a[1]
    elif base == "div_s":
        if a[1] == 0:
            r = a[2]
        else:
            x, y = _as_signed(a[0], n), _as_signed(a[1], n)
            q = abs(x) // abs(y)
            r = q if (x < 0) == (y < 0) else -q
    elif base == "rem_u":
        r = a[0] if a[1] == 0 else a[0] % a[1]
    elif base == "rem_s":
        if a[1] == 0:
            r = a[0]
        else:
            x, y = _as_signed(a[0], op.inputs[0]), _as_signed(a[1], op.inputs[0])
            r = abs(x) % abs(y) * (-1 if x < 0 else 1)
    elif base == "select":
        r = a[1] if a[0] else a[2]
    elif base == "extend_zero":
        r = a[0]
    elif base == "extend_sign":
        r = _as_signed(a[0], op.inputs[0])
    elif base == "extract_low":
        r = a[0]
    else:
        raise NotImplementedError(base)
    return [int(r) & _bit_mask(o)]


class LowBitsRegisterFileView:
    """View the low bits of another register file.

    An `alias.<file>@0+<width>` write clears the bits above the view.
    """

    def __init__(self, owner: "list[int] | LowBitsRegisterFileView", width: int):
        self.owner, self.mask = owner, _bit_mask(width)

    def __len__(self):
        return len(self.owner)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [v & self.mask for v in self.owner[i]]
        return self.owner[i] & self.mask

    def __setitem__(self, i, v):
        if isinstance(i, slice):
            for k, x in zip(range(len(self.owner))[i], v):
                self.owner[k] = x & self.mask
        else:
            self.owner[i] = v & self.mask


class Machine:
    def __init__(self, arch: Arch, vq: int = 1, *, max_statements: int | None = None):
        self.arch = arch
        self.remaining_statements = max_statements
        self._helper_depth = 0
        self.vq = vq
        self.ops = {o.name: o for o in arch.operations}
        self.snippets = {s.name: s for s in arch.snippets}
        self.tables = {t.name: t for t in arch.tables_int}
        self.instrs = {i.name: i for i in arch.instructions}
        self.regs: dict[str, list[int] | LowBitsRegisterFileView] = {
            rf.name: [0] * rf.regs_num() for rf in arch.register_files
        }
        aliases: dict[str, tuple[str, int]] = {}
        for rf in arch.register_files:
            for a in rf.attributes:
                m = re.fullmatch(r"alias\.(\w+)@0\+(\d+)", a)
                if m and m.group(1) in self.regs:
                    aliases[m.group(1)] = (rf.name, int(m.group(2)))

        resolving: set[str] = set()

        def resolve(name: str) -> list[int] | LowBitsRegisterFileView:
            if name not in aliases:
                return self.regs[name]
            if name in resolving:
                raise ValueError(f"cyclic register file alias: {name}")
            resolving.add(name)
            owner, width = aliases[name]
            self.regs[name] = LowBitsRegisterFileView(resolve(owner), width)
            resolving.remove(name)
            del aliases[name]
            return self.regs[name]

        # Resolve owners before their views, regardless of declaration order.
        for name in list(aliases):
            resolve(name)
        self.env: dict[str, Callable] = {}
        self.dyn: dict[str, int] = {}

    def lanes(self, shape) -> int:
        if shape.lanes_mult is None:
            return shape.lanes_base
        return (
            shape.lanes_base
            * {"VQ": self.vq, "VQVQ": self.vq * self.vq}[shape.lanes_mult]
        )

    def run_op(self, op: Operation, args: list[int]) -> list[int]:
        """Evaluate an operation on scalar (single-lane) arguments."""
        if op.semantic_base:
            return _std(op.semantic_base, op, args)
        if op.semantic_table:
            return [self.tables[op.semantic_table].values[args[0]]]
        self._helper_depth += 1
        try:
            if self._helper_depth > 64:
                raise ValueError("helper call depth limit exceeded")
            return [
                v[0]
                for v in self.run(
                    self.snippets[op.semantic_func].seq, [[a] for a in args]
                )
            ]
        finally:
            self._helper_depth -= 1

    def _rf_size(self, name):
        return next(
            self.lanes(rf.reg_size)
            for rf in self.arch.register_files
            if rf.name == name
        )

    def run(self, seq: StatementSeq, inputs: list[list[int]]) -> list[list[int]]:
        """Execute a sequence; every value is a list of lanes."""
        vals: dict[str, list[int]] = {}
        outputs: dict[int, list[int]] = {}
        for st in seq.stmts:
            if self.remaining_statements is not None:
                self.remaining_statements -= 1
                if self.remaining_statements < 0:
                    raise ValueError("native statement execution limit exceeded")
            n = self.lanes(st.shape)
            args = [vals[i] for i in st.inputs]
            k, spec = st.kind, st.specifier

            def lanewise(fn, n=n, args=args, st=st):
                assert all(len(a) == n for a in args), st
                outs = [fn([a[i] for a in args]) for i in range(n)]
                return (
                    [list(c) for c in zip(*outs)]
                    if outs and outs[0]
                    else [[] for _ in st.outputs]
                )

            if k == "input":
                res = [inputs[int(spec)]]
            elif k == "output":
                outputs[int(spec)] = args[0]
                res = []
            elif k == "const":
                res = [[int(spec)] * n]
            elif k == "dyn_const":
                res = [[self.dyn[spec]] * n]
            elif k == "read":
                w = st.outputs_types[0]
                assert n * w == self._rf_size(spec), st
                reg = self.regs[spec][args[0][0]]
                res = [[(reg >> (i * w)) & _bit_mask(w) for i in range(n)]]
            elif k == "write":
                idx, value = args
                w = self._rf_size(spec) // n
                assert len(value) == n
                self.regs[spec][idx[0]] = sum(v << (i * w) for i, v in enumerate(value))
                res = []
            elif k == "op":
                res = lanewise(lambda a, spec=spec: self.run_op(self.ops[spec], a))
            elif k == "env":
                res = lanewise(lambda a, spec=spec: self.env[spec](*a) or [])
            elif k == "cond_env":
                nin = len(args) - 1 - len(st.outputs)
                res = lanewise(
                    lambda a, spec=spec, nin=nin: (
                        (self.env[spec](*a[1 : 1 + nin]) or [])
                        if a[0]
                        else a[1 + nin :]
                    )
                )
            elif k == "index":
                res = [list(range(n))]
            elif k == "gather":
                value, index, default = args
                res = [
                    [
                        value[j] if j < len(value) else default[i]
                        for i, j in enumerate(index)
                    ]
                ]
            elif k == "replicate":
                res = [[args[0][0]] * n]
            elif k == "extract_first":
                res = [args[0][:n]]
            elif k == "extend_zero":
                res = [args[0] + [0] * (n - len(args[0]))]
            elif k == "fold":
                width = len(st.outputs)
                state = [a[0] for a in args[:width]]
                vectors = args[width:]
                for lane in range(len(vectors[0])):
                    state = self.run_op(
                        self.ops[spec], state + [v[lane] for v in vectors]
                    )[:width]
                res = [[v] for v in state]
            else:
                raise NotImplementedError(k)
            assert len(res) == len(st.outputs), st
            for name, w, v in zip(st.outputs, st.outputs_types, res):
                assert all(0 <= x <= _bit_mask(w) for x in v), (st, v)
                assert len(v) == (1 if k == "fold" else n), st
                vals[name] = v
        return [outputs[i] for i in sorted(outputs)]

    def run_scalar(self, seq: StatementSeq, inputs: list[int]) -> list[int]:
        return [v[0] for v in self.run(seq, [[i] for i in inputs])]

    # -- encoding helpers ------------------------------------------------------
    def encode(self, ins: Instruction, operands: list[int]) -> int:
        self.dyn["enc_base"] = ins.encoding.const_encoding_part
        return self.run_scalar(self.snippets[ins.encoding.encode].seq, operands)[0]

    def decode_operands(self, ins: Instruction, word: int) -> list[int]:
        """Extract raw operands using the given instruction's encoding."""
        return [
            self.run_scalar(self.snippets[d].seq, [word])[0]
            for d in ins.encoding.decode
        ]

    def valid_operands(self, ins: Instruction, operands: list[int]) -> bool:
        c = ins.encoding.constraint_encode
        return not c or bool(self.run_scalar(self.snippets[c].seq, operands)[0])

    def valid_word(self, ins: Instruction, word: int) -> bool:
        e = ins.encoding
        if word & e.const_mask != e.const_encoding_part:
            return False
        return not e.constraint_decode or bool(
            self.run_scalar(self.snippets[e.constraint_decode].seq, [word])[0]
        )

    def execute(self, ins: Instruction, operands: list[int]):
        self.run_scalar(ins.semantic, operands)

    def decode_word(self, word: int) -> tuple[Instruction, list[int]]:
        """Return the single matching instruction and its raw operands.

        Raise ValueError if the 32-bit word has zero or multiple matches.
        """
        if not 0 <= word < (1 << 32):
            raise ValueError("word must be a 32-bit unsigned integer")
        matches = []
        for ins in self.arch.instructions:
            if ins.encoding.encoded_size == 32 and self.valid_word(ins, word):
                operands = self.decode_operands(ins, word)
                if self.valid_operands(ins, operands):
                    matches.append((ins, operands))
        if not matches:
            raise ValueError(f"no instruction decodes word {word:#010x}")
        if len(matches) != 1:
            names = ", ".join(ins.name for ins, _ in matches)
            raise ValueError(f"ambiguous decode for {word:#010x}: {names}")
        return matches[0]

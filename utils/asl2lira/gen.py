"""Generate the LIRA description of A64 instructions from Arm XML."""

from pathlib import Path

from lira import arch_ser_yaml
from lira.arch import Arch, Instruction, InstructionEncoding
from lira.ir_builder import InstructionBuilder, SnippetBuilder, Value

from . import xmlspec
from .insns_a64 import EXCLUDE, GROUPS, KEEP, SEM, SPECS
from .lib import Ctx, S


def _decode_snippet(ctx: Ctx, f: xmlspec.Field) -> str:
    """`[32 -> field]`: extract one operand field from the instruction word."""
    name = f"decode_field_{f.lo}_{f.width}"
    if name not in ctx.snippets:
        sb = SnippetBuilder(name)
        s = S(ctx, sb)
        sb.output(s.bits(sb.input(0, 32), f.lo, f.width), 0)
        ctx.add_snippet(sb, dedup=False)
    return name


def _encode_snippet(ctx: Ctx, e: xmlspec.Encoding) -> str:
    """`[operands] -> 32`: `enc_base` is the encoding's const_encoding_part."""
    sig = "_".join(f"{f.lo}w{f.width}" for f in e.operands) or "none"
    name = f"encode_{sig}"
    if name not in ctx.snippets:
        sb = SnippetBuilder(name)
        s = S(ctx, sb)
        acc = sb.dyn_const("enc_base", 32)
        for i, f in enumerate(e.operands):
            v = s.zext(sb.input(i, f.width), 32)
            if f.lo:
                v = s.lsl(v, s.c(f.lo, 32))
            acc = s.orr(acc, v)
        sb.output(acc, 0)
        ctx.add_snippet(sb, dedup=False)
    return name


def resolve_overlaps(encs: dict[str, xmlspec.Encoding]):
    """A more specific encoding wins over a general one it is contained in (the
    XML's `See(...)`, e.g. HINT vs. PACIASP): the general one excludes it."""
    all_encs = list(encs.values())
    for e in all_encs:
        e.excluded = []
        for f in all_encs:
            if f is e or (f.const_mask & e.const_mask) != e.const_mask:
                continue
            if (
                f.const_mask != e.const_mask
                and (f.const_value & e.const_mask) == e.const_value
            ):
                e.excluded.append(
                    (f.const_mask & ~e.const_mask, f.const_value & ~e.const_mask)
                )


def _word(s: S, e: xmlspec.Encoding, F) -> Value:
    """The operand bits of the instruction word (fixed bits are zero)."""
    acc = s.c(0, 32)
    for f in e.operands:
        v = s.zext(F(f.name), 32)
        acc = s.orr(acc, s.lsl(v, s.c(f.lo, 32)) if f.lo else v)
    return acc


def _validity(s: S, e: xmlspec.Encoding, F, undef, word: Value = None) -> Value:
    """1 iff the operand fields form an allocated (not UNDEFINED) encoding.
    `word` is the instruction word when it is at hand (constraint_decode)."""
    bad = []
    if getattr(e, "excluded", None):
        if word is None:
            word = _word(s, e, F)
        masked: dict[int, Value] = {}
        for m, v in e.excluded:
            if m not in masked:
                masked[m] = s.and_(word, s.c(m, 32))
            bad.append(s.eqc(masked[m], v))
    for fname, pat in e.ne:  # `field != pattern` in XML
        m = int(pat.replace("0", "1").replace("x", "0"), 2)
        v = int(pat.replace("x", "0"), 2)
        w = e.fields[fname].width
        bad.append(s.eqc(s.and_(F(fname), s.c(m, w)), v))
    if undef is not None:
        u = undef(s, e, F)
        if u is not None:
            bad.append(u)
    return s.not_(s.or1(*bad)) if bad else None


def _constraint_snippets(ctx: Ctx, e: xmlspec.Encoding, undef):
    # constraint_encode: operands -> 1; also checks bits the encoding fixes
    sb = SnippetBuilder(f"constraint_encode_{e.name}")
    s = S(ctx, sb)
    vals = {f.name: sb.input(i, f.width) for i, f in enumerate(e.operands)}
    F = _field_accessor(s, e, vals)
    checks = []
    for f in e.operands:
        m, v = e.fixed_bits(f.name)
        if m:
            checks.append(s.eqc(s.and_(vals[f.name], s.c(m, f.width)), v))
    ok = _validity(s, e, F, undef)
    if ok is not None:
        checks.append(ok)
    if not checks:
        return "", ""
    sb.output(s.and1(*checks), 0)
    enc_name = ctx.add_snippet(sb)

    # constraint_decode: instruction word -> 1 (fixed bits are matched by the decoder)
    ok_needed = ok is not None
    if not ok_needed:
        return "", enc_name
    sb = SnippetBuilder(f"constraint_decode_{e.name}")
    s = S(ctx, sb)
    word = sb.input(0, 32)
    sb.output(_validity(s, e, _field_accessor(s, e, {}, word), undef, word), 0)
    return ctx.add_snippet(sb), enc_name


def _field_accessor(
    s: S, e: xmlspec.Encoding, vals: dict[str, Value], word: Value = None
):
    """F(name): an operand value, a field extracted from `word` on first use,
    or the constant value of a fixed field."""
    operands = {f.name: f for f in e.operands}

    def F(name: str) -> Value:
        if name not in vals:
            if word is not None and name in operands:
                f = operands[name]
                vals[name] = s.bits(word, f.lo, f.width)
            else:
                v = e.fixed(name)
                assert v is not None, (
                    f"{e.name}: field {name} is neither operand nor fixed"
                )
                vals[name] = s.c(v, e.fields[name].width)
        return vals[name]

    return F


def build_instruction(ctx: Ctx, e: xmlspec.Encoding) -> Instruction:
    handler, undef = SEM[e.file]
    constraint_decode, constraint_encode = _constraint_snippets(ctx, e, undef)
    encoding = InstructionEncoding(
        encoded_size=32,
        const_encoding_part=e.const_value,
        const_mask=e.const_mask,
        decode=[_decode_snippet(ctx, f) for f in e.operands],
        encode=_encode_snippet(ctx, e),
        constraint_decode=constraint_decode,
        constraint_encode=constraint_encode,
    )
    ib = InstructionBuilder(
        e.name, [f.width for f in e.operands], [f.name for f in e.operands], encoding
    )
    s = S(ctx, ib)
    vals = {f.name: ib.add_input_operand(i, f.width) for i, f in enumerate(e.operands)}
    handler(s, e, _field_accessor(s, e, vals))
    ctx.collect_ops(ib)
    instr = ib.build()
    instr.attributes = [f"{k}.{v}" for k, v in sorted(e.docvars.items()) if k != "isa"]
    return instr


def load_encodings(
    xml_dir: Path, files, in_place: bool = True
) -> dict[str, xmlspec.Encoding]:
    """The encodings of `files`, specialized (SPECS) and filtered (EXCLUDE, KEEP).
    Specializations take the place of their encoding, so instructions follow the
    file order; without `in_place` they come after all the other encodings (the
    historical order of the first group)."""
    encs = xmlspec.load(xml_dir, files)
    for name in EXCLUDE & encs.keys():
        del encs[name]
    out: dict[str, xmlspec.Encoding] = {}
    later: dict[str, xmlspec.Encoding] = {}
    for name, e in encs.items():
        if not all(keep(e) for keep in KEEP):
            continue
        spec_list = SPECS.get(e.file)
        if callable(spec_list):
            spec_list = spec_list(e)
        if not spec_list:
            out[name] = e
            continue
        for suffix, fixed in spec_list:
            spec = xmlspec.specialize(e, suffix, fixed)
            (out if in_place else later)[spec.name] = spec
    out.update(later)
    return out


def build_arch(xml_dir: Path) -> Arch:
    ctx = Ctx()
    encs: dict[str, xmlspec.Encoding] = {}
    for i, files in enumerate(GROUPS):  # a later group appends its instructions
        encs.update(load_encodings(xml_dir, files, in_place=i > 0))
    resolve_overlaps(encs)
    instructions = [build_instruction(ctx, e) for e in encs.values()]
    return Arch(
        name="AArch64",
        attributes=["isa.A64", "endianness.little"],
        register_files=[
            ctx.rf_x, ctx.rf_nzcv, ctx.rf_v, ctx.rf_fpcr, ctx.rf_fpsr,
            ctx.rf_z, ctx.rf_p, ctx.rf_ffr, ctx.rf_za, ctx.rf_svcr,
        ],
        system_registers=[],
        environment_functions=list(ctx.envs.values()),
        tables_int=list(ctx.tables.values()),
        operations=list(ctx.ops.values()),
        snippets=list(ctx.snippets.values()),
        instructions=instructions,
        float_operations=list(ctx.fops.values()),
    )


def write_yaml(arch: Arch, path: Path):
    arch_ser_yaml.write_arch(arch, path)
    assert arch_ser_yaml.read_arch(path) == arch, "YAML round trip mismatch"

    print(
        f"{path}: {len(arch.instructions)} instructions, "
        f"{len(arch.operations)} operations, {len(arch.snippets)} snippets"
    )

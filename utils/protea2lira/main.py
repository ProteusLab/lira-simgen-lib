#!/usr/bin/env python3

# Convert the native Protea IR (PIR) into LIRA IR

import argparse
from pathlib import Path

from ruamel.yaml import YAML

from lira import arch, ir_ops
from lira.arch_ser_yaml import write_arch
from lira.ir import Shape
from lira.ir_builder import ArchBuilder, InstructionBuilder, SnippetBuilder, Value
from lira.ir_ops import BaseOp

from lib.snippet import SnippetKind

from utils.protea2lira.context import (
    PC_ATTRIBUTE,
    Context,
    Scope,
    find_env,
    is_signed,
    is_unsigned,
    width_of,
)

CMP_METHODS = dict(
    (
        ("eq", BaseOp.EQ),
        ("ne", BaseOp.NE),
        ("lt", BaseOp.SLT),
        ("gt", BaseOp.SGT),
        ("le", BaseOp.SLE),
        ("ge", BaseOp.SGE),
    )
)
CMP_METHODS_U = dict(
    (
        ("lt", BaseOp.ULT),
        ("gt", BaseOp.UGT),
        ("le", BaseOp.ULE),
        ("ge", BaseOp.UGE),
    )
)

# Canonical-IR kinds that are Python keywords.
_ALIASES = dict((("and", "and_"), ("or", "or_")))


def resolve(node, scope):
    """Resolve a native Protea IR value reference to a LIRA Value."""
    if isinstance(node, int):
        return scope.seq.const(node, 32)

    if node.get("value") is not None:
        return scope.seq.const(node["value"], 32)

    name = node["name"]

    if name in scope.vars:
        value = scope.vars[name]
        if isinstance(value, Value):
            return value
        raise ValueError(f"variable '{name}' is used before it is assigned")

    if name in scope.operand_names:
        operand = scope.seq.input(
            scope.operand_names.index(name), width_of(node["type"])
        )

        scope.vars[name] = operand
        if node.get("regset"):
            operand = scope.seq.read(scope.ctx.reg_files[node["regset"]], operand)
            scope.vars[name] = operand

        return operand

    if name in scope.ctx.pc_regs:
        value = scope.seq.env(scope.ctx.get_pc, list())[0]
        scope.vars[name] = value
        return value
    raise ValueError(f"unresolved variable '{name}'")


def truncate(scope, value, width):
    if value.width == width:
        return value
    return scope.seq.extract_low(value, width)


def extend(scope, value, width, signed):
    if value.width == width:
        return value
    if signed:
        return scope.seq.extend_sign(value, width)
    return scope.seq.extend_zero(value, width)


def extract_field(scope, field_var, dest_type):
    field = scope.fields[field_var]
    lo, hi = field["to"], field["from"]
    width = hi - lo + 1
    shifted = scope.seq.lsr(scope.raw, scope.seq.const(lo, 32))
    value = scope.seq.extract_low(shifted, width)
    return extend(scope, value, width_of(dest_type), signed=is_signed(dest_type))


def new_var(stmt, scope):
    scope.vars[stmt["oprnds"][0]["name"]] = width_of(stmt["oprnds"][0]["type"])


def let(stmt, scope):
    lhs, rhs = stmt["oprnds"]
    if rhs.get("name") and rhs["name"] in scope.fields:
        value = extract_field(scope, rhs["name"], lhs["type"])
    else:
        value = resolve(rhs, scope)
    scope.vars[lhs["name"]] = value


def cast(stmt, scope):
    lhs, rhs = stmt["oprnds"]
    current = scope.vars.get(rhs["name"]) if rhs.get("name") else None

    if isinstance(current, Value):
        value = truncate(scope, current, width_of(rhs["type"]))
        # Only 's' types sign-extend; 'b' (raw bits) and 'u' zero-extend.
        value = extend(
            scope, value, width_of(lhs["type"]), signed=is_signed(lhs["type"])
        )
    elif rhs.get("name") and rhs["name"] in scope.fields:
        value = extract_field(scope, rhs["name"], lhs["type"])
    else:
        value = resolve(rhs, scope)

    scope.vars[lhs["name"]] = value


def _bin(stmt, scope, op):
    lhs, left, right = stmt["oprnds"]
    method = "and_" if op is BaseOp.AND else op
    value = getattr(scope.seq, method)(resolve(left, scope), resolve(right, scope))
    scope.vars[lhs["name"]] = value


def add(stmt, scope):
    return _bin(stmt, scope, BaseOp.ADD)


def sub(stmt, scope):
    return _bin(stmt, scope, BaseOp.SUB)


def mul(stmt, scope):
    return _bin(stmt, scope, BaseOp.MUL)


def and_(stmt, scope):
    return _bin(stmt, scope, BaseOp.AND)


def xor(stmt, scope):
    return _bin(stmt, scope, BaseOp.XOR)


def _mixed(stmt, scope, cls):
    # semantic trees legitimately mix operand widths
    lhs, left, right = stmt["oprnds"]
    left_val = resolve(left, scope)
    scope.vars[lhs["name"]] = scope.seq.op(
        cls(left_val.width), list((left_val, resolve(right, scope)))
    )


def shl(stmt, scope):
    return _mixed(stmt, scope, ir_ops.Lsl)


def ashr(stmt, scope):
    return _mixed(stmt, scope, ir_ops.Asr)


def or_(stmt, scope):
    return _mixed(stmt, scope, ir_ops.Orr)


def shr(stmt, scope):
    if is_signed(stmt["oprnds"][1]["type"]):
        _mixed(stmt, scope, ir_ops.Asr)
    else:
        _mixed(stmt, scope, ir_ops.Lsr)


def _cmp(stmt, scope, kind):
    lhs, left, right = stmt["oprnds"]
    table = CMP_METHODS_U if is_unsigned(left["type"]) else CMP_METHODS
    method = table.get(kind)

    if method is None:
        raise ValueError(f"no comparison operation '{kind}'")

    scope.vars[lhs["name"]] = getattr(scope.seq, method)(
        resolve(left, scope), resolve(right, scope)
    )


def lt(stmt, scope):
    return _cmp(stmt, scope, "lt")


def gt(stmt, scope):
    return _cmp(stmt, scope, "gt")


def le(stmt, scope):
    return _cmp(stmt, scope, "le")


def ge(stmt, scope):
    return _cmp(stmt, scope, "ge")


def eq(stmt, scope):
    return _cmp(stmt, scope, "eq")


def ne(stmt, scope):
    return _cmp(stmt, scope, "ne")


def select(stmt, scope):
    lhs, cond, true_val, false_val = stmt["oprnds"]
    scope.vars[lhs["name"]] = scope.seq.select(
        resolve(cond, scope), resolve(true_val, scope), resolve(false_val, scope)
    )


def extract(stmt, scope):
    lhs, src, high, low = stmt["oprnds"]
    scope.vars[lhs["name"]] = scope.seq.extract_low(
        resolve(src, scope), high["value"] - low["value"] + 1
    )


def readReg(stmt, scope):
    scope.vars[stmt["oprnds"][0]["name"]] = resolve(stmt["oprnds"][1], scope)


def writeReg(stmt, scope):
    reg, rhs = stmt["oprnds"]
    value, name = resolve(rhs, scope), reg["name"]

    if name in scope.operand_names:
        operand = scope.seq.input(
            scope.operand_names.index(name), width_of(reg["type"])
        )
        scope.seq.write(scope.ctx.reg_files[reg["regset"]], operand, value)
    elif name in scope.ctx.pc_regs:
        scope.seq.env(scope.ctx.set_pc, list((value,)))
    else:
        raise ValueError(f"unresolved write register '{name}'")


def readMem(stmt, scope):
    lhs, addr = stmt["oprnds"]
    addr_val = resolve(addr, scope)
    env = find_env(
        scope.ctx,
        stmt["attrs"],
        list((addr_val.width,)),
        list((width_of(lhs["type"]),)),
    )
    scope.vars[lhs["name"]] = scope.seq.env(env, list((addr_val,)))[0]


def writeMem(stmt, scope):
    addr, rhs = stmt["oprnds"]
    addr_val, value = resolve(addr, scope), resolve(rhs, scope)
    env = find_env(
        scope.ctx,
        stmt["attrs"],
        list((addr_val.width, value.width)),
        list(),
    )
    scope.seq.env(env, list((addr_val, value)))


def branch(stmt, scope):
    scope.seq.env(scope.ctx.set_pc, list((resolve(stmt["oprnds"][0], scope),)))


def sysCall(stmt, scope):
    scope.seq.env(find_env(scope.ctx, stmt["name"], list(), list()), list())


def rem(stmt, scope):
    lhs, left, right = stmt["oprnds"]
    left_val, right_val = resolve(left, scope), resolve(right, scope)
    method = BaseOp.REM_U if is_unsigned(left["type"]) else BaseOp.REM_S
    scope.vars[lhs["name"]] = getattr(scope.seq, method)(left_val, right_val)


def div(stmt, scope):
    lhs, left, right = stmt["oprnds"]
    left_val, right_val = resolve(left, scope), resolve(right, scope)
    default = scope.seq.const(0, left_val.width)
    method = BaseOp.DIV_U if is_unsigned(left["type"]) else BaseOp.DIV_S
    scope.vars[lhs["name"]] = getattr(scope.seq, method)(left_val, right_val, default)


def emit(stmt, scope):
    kind = stmt["name"]
    handler = globals().get(_ALIASES.get(kind, kind))
    if not callable(handler):
        raise ValueError(f"unsupported statement '{kind}'")
    handler(stmt, scope)


def find_operand_var(statements):
    for stmt in statements:
        if stmt["name"] != "new_var":
            continue
        if "op" in (stmt.get("attrs") or list()):
            return stmt["oprnds"][0]

    raise ValueError("operand tree has no [:op]-marked variable")


def collect_ops(ctx, builder):
    ctx.used.update(builder.operations_map)


def build_decode_snippets(ctx, fields_by_name, operand_map, operand_list):
    names = list()

    for operand in operand_list:
        tree = operand_map[operand]
        builder = SnippetBuilder(name="temp_operand")
        scope = Scope(ctx, builder, fields=fields_by_name)
        scope.raw = builder.input(0, 32)

        for stmt in tree["tree"]:
            emit(stmt, scope)

        var = find_operand_var(tree["tree"])
        builder.output(scope.vars[var["name"]], 0)
        collect_ops(ctx, builder)
        names.append(ctx.add_snippet(builder.build(), SnippetKind.DECODE))

    return names


def build_encode_snippet(ctx, fields, operand_names, field_positions, operand_vars):
    builder = SnippetBuilder(name="temp_encode")
    scope = Scope(ctx, builder)
    operands = list(
        builder.input(index, width_of(var["type"]))
        for index, var in enumerate(operand_vars)
    )

    base = builder.const(0, 32)

    for field in fields:
        lo, hi = field["to"], field["from"]
        width = hi - lo + 1
        name = field["value"]["name"]
        value_num = field["value"].get("value_num")

        if value_num is not None:
            value = extend(scope, builder.const(value_num, width), 32, signed=False)
        elif name in field_positions:
            operand, shift = field_positions[name]
            value = operands[operand_names.index(operand)]
            if shift:
                value = scope.seq.lsr(value, scope.seq.const(shift, 32))
            value = extend(scope, scope.seq.extract_low(value, width), 32, signed=False)
        else:
            raise ValueError(f"field '{name}' has no constant and no operand")

        value = scope.seq.lsl(value, scope.seq.const(lo, 32))
        base = scope.seq.orr(base, value)

    builder.output(base, 0)
    collect_ops(ctx, builder)

    return ctx.add_snippet(builder.build(), SnippetKind.ENCODE)


def field_map(operand_map, operand_list, fields):
    field_names = set(f["value"]["name"] for f in fields)
    mapping = dict()

    def parts_of(node, parts):
        if node.get("value") is not None:
            return list()
        name = node["name"]
        if name in field_names:
            return list(((name, 0),))
        if name not in parts:
            raise ValueError(f"operand tree references undefined variable '{name}'")
        return parts[name]

    for operand in operand_list:
        parts = dict()

        for stmt in operand_map[operand]["tree"]:
            if stmt["name"] == "new_var":
                continue

            lhs = stmt["oprnds"][0]
            if not lhs.get("name"):
                continue

            if stmt["name"] == "shl":
                parts[lhs["name"]] = list(
                    (f, s + stmt["oprnds"][2]["value"])
                    for f, s in parts_of(stmt["oprnds"][1], parts)
                )

            elif stmt["name"] == "or":
                parts[lhs["name"]] = parts_of(stmt["oprnds"][1], parts) + parts_of(
                    stmt["oprnds"][2], parts
                )

            else:
                parts[lhs["name"]] = parts_of(stmt["oprnds"][1], parts)

        for field, shift in parts[operand]:
            if field in mapping and mapping[field] != (operand, shift):
                raise ValueError(f"conflicting derivation for field '{field}'")
            mapping[field] = (operand, shift)

    return mapping


def convert_instruction(ctx, instr):
    name = instr["name"]
    fields = instr.get("fields") or list()
    operand_map = instr.get("operand_map") or dict()
    operand_list = instr.get("operand_list") or list()

    operand_vars = list(
        find_operand_var(operand_map[operand]["tree"]) for operand in operand_list
    )

    operand_names = list(var["name"] for var in operand_vars)
    operand_sizes = list(width_of(var["type"]) for var in operand_vars)

    placeholder = arch.InstructionEncoding(
        encoded_size=32,
        const_encoding_part=0,
        const_mask=0,
        decode=list(),
        encode="",
        constraint_decode="",
        constraint_encode="",
    )
    sem_builder = InstructionBuilder(
        name=name, operand_sizes=list(), operand_names=list(), encoding=placeholder
    )

    scope = Scope(ctx, sem_builder, operand_names=operand_names)

    try:
        for stmt in instr["code"].get("tree") or list():
            emit(stmt, scope)
    except ValueError as error:
        raise ValueError(f"instruction {name}: {error}") from error

    semantic = sem_builder.build().semantic
    collect_ops(ctx, sem_builder)

    fields_by_name = dict((f["value"]["name"], f) for f in fields)
    if operand_map and operand_vars:
        decode_snippets = build_decode_snippets(
            ctx, fields_by_name, operand_map, operand_list
        )
        field_positions = field_map(operand_map, operand_list, fields)
    else:
        decode_snippets, field_positions = list(), dict()

    encode_snippet = (
        build_encode_snippet(ctx, fields, operand_names, field_positions, operand_vars)
        if fields and operand_vars
        else ""
    )

    const_part = const_mask = 0
    for field in fields:
        value_num = field["value"].get("value_num")
        if value_num is not None:
            lo, hi = field["to"], field["from"]
            const_part |= value_num << lo
            const_mask |= ((1 << (hi - lo + 1)) - 1) << lo

    builder = SnippetBuilder(name="temp_constraint")
    raw = builder.input(0, 32)
    masked = builder.and_(raw, builder.const(const_mask, 32))
    result = builder.eq(masked, builder.const(const_part, 32))
    builder.output(result, 0)

    collect_ops(ctx, builder)

    constraint_decode = ctx.add_snippet(builder.build(), SnippetKind.CONSTRAINT)

    encoding = arch.InstructionEncoding(
        encoded_size=32,
        const_encoding_part=const_part,
        const_mask=const_mask,
        decode=decode_snippets,
        encode=encode_snippet,
        constraint_decode=constraint_decode,
        constraint_encode="",
    )

    return arch.Instruction(
        name=name,
        attributes=list(),
        operand_sizes=operand_sizes,
        operand_names=operand_names,
        encoding=encoding,
        semantic=semantic,
    )


def convert(ir_data):
    arch_name = ir_data["instructions"][0]["feature"]
    reg_files, pc_regs = dict(), set()
    pc_size = None

    for ir_rf in ir_data["regfiles"]:
        rf_name = ir_rf["name"]

        regs = list(
            arch.Register(name=reg["name"], attributes=reg.get("attrs") or list())
            for reg in ir_rf["regs"]
        )

        reg_files[rf_name] = arch.RegisterFile(
            name=rf_name,
            attributes=list(),
            reg_size=Shape(lanes_base=32, lanes_mult=None),
            regs=regs,
        )

        for reg in ir_rf["regs"]:
            if PC_ATTRIBUTE in (reg.get("attrs") or list()):
                pc_regs.add(reg["name"])
                pc_size = reg["size"]

    if pc_size is None:
        raise ValueError(
            "native Protea IR has no register marked with the 'pc' attribute"
        )

    envs = list(
        arch.EnvironmentFunction(
            name=entry["name"],
            attributes=entry.get("attrs") or list(),
            inputs=list(width_of(t) for t in entry["argument_types"]),
            outputs=list(width_of(t) for t in entry["return_types"]),
        )
        for entry in ir_data["interface_functions"]
    )

    get_pc = arch.EnvironmentFunction(
        name="getPC",
        attributes=list((PC_ATTRIBUTE,)),
        inputs=list(),
        outputs=list((pc_size,)),
    )
    set_pc = arch.EnvironmentFunction(
        name="setPC",
        attributes=list((PC_ATTRIBUTE,)),
        inputs=list((pc_size,)),
        outputs=list(),
    )

    envs += list((get_pc, set_pc))

    builder = ArchBuilder(name=arch_name, attributes=list())

    for reg_file in reg_files.values():
        builder.add_register_file(reg_file)

    for env in envs:
        builder.add_env_func(env)

    ctx = Context(builder, reg_files, pc_regs, envs, get_pc, set_pc)

    for instr in ir_data["instructions"]:
        builder.add_instruction(convert_instruction(ctx, instr))

    for op in ctx.used.values():
        builder.add_operation(op)
    return builder.build()


def main():
    parser = argparse.ArgumentParser(
        description="Convert the native Protea IR (PIR) into LIRA IR"
    )
    parser.add_argument(
        "--ir-path",
        type=Path,
        required=True,
        help="path to the native Protea IR (PIR) produced by Protea's serializer",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="path of the LIRA IR file to write",
    )
    args = parser.parse_args()

    yaml = YAML(typ="safe")
    with open(args.ir_path) as stream:
        ir_data = yaml.load(stream)

    arch_obj = convert(ir_data)
    write_arch(arch_obj, args.output)
    print(f"Serialized architecture '{arch_obj.name}' to {args.output}")


if __name__ == "__main__":
    main()

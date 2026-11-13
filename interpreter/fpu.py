import re


_FLAGS = {
    "invalid": "kInvalid",
    "divbyzero": "kDivByZero",
    "overflow": "kOverflow",
    "underflow": "kUnderflow",
    "inexact": "kInexact",
    "input_denormal": "kInputDenormal",
}


def float_call(name, cpu, args):
    operation = re.fullmatch(
        r"([a-z]+)_(\d+)(?:_to_(\d+))?(_default_nan)?(_no_flags)?", name
    )
    if operation is None:
        raise ValueError(f"Unknown float operation {name}")
    base, source, dest, default_nan, no_flags = operation.groups()
    widths = f"{source}, {dest}" if dest else source
    arguments = ", ".join(["fpu", *args])
    lines = [f"auto fpu = fpuState({cpu});"]
    if default_nan:
        lines.append("fpu.dn = true;")
    lines.append(f"const auto result = prot::fp::{base}<{widths}>({arguments});")
    if not no_flags:
        lines.append(f"fpuUpdate({cpu}, fpu);")
    lines.append("return result;")
    return "[&] { " + " ".join(lines) + " }()"


def fpu_helpers(arch, state):
    bindings = {}
    fields = {}
    for register_file in arch.register_files:
        model = state.registers[register_file.name]
        for index, reg in enumerate(register_file.regs):
            for attr in reg.attributes:
                name = attr.name + (f"@{attr.value}" if attr.value else "")
                if name in ("fpu.control", "fpu.status"):
                    bindings[name] = model, index
                field = re.fullmatch(r"fpu\.(\w+|flag\.\w+)@(\d+)(?:\+(\d+))?", name)
                if field is not None:
                    fields[field[1]] = int(field[2]), int(field[3] or 1)
    if not bindings:
        return ""
    control, ci = bindings["fpu.control"]
    status, si = bindings["fpu.status"]

    def read_field(name):
        lsb, width = fields.get(name, (0, 0))
        return f"(control >> {lsb}) & {(1 << width) - 1}" if width else "0"

    controls = "\n".join(
        f"  st.{name} = {read_field(name)};" for name in ("rmode", "fz", "fz16", "dn")
    )
    flags = "\n".join(
        f"  if (st.flags & prot::fp::{flag}) status |= uint64_t{{1}} << {fields[f'flag.{name}'][0]};"
        for name, flag in _FLAGS.items() if f"flag.{name}" in fields
    )
    return f"""\
prot::fp::State fpuState(const CPU& cpu) {{
  const auto control = {control.read(ci)};
  prot::fp::State st;
{controls}
  return st;
}}

void fpuUpdate(CPU& cpu, const prot::fp::State& st) {{
  uint64_t status = {status.read(si)};
{flags}
  {status.write(si, "status")}
}}"""

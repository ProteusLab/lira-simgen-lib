# AArch64 ASL XML to LIRA IR converter

Converts selected A64 instruction encodings from the Arm machine-readable XML
specification into LIRA IR. The XML supplies encoding fields and constraints;
instruction semantics are implemented in the `insns_*.py` modules. This is not
a general ASL pseudocode translator.

## CMake

Point `ASL_XML_DIR` at the directory containing instruction files such as
`add_addsub_imm.xml`:

```bash
cmake -S . -B build/aarch64 \
  -DARCH_SOURCE=ASL \
  -DARCH_TARGET=AArch64 \
  -DASL_XML_DIR=/path/to/ISA_A64_xml_A_profile
cmake --build build/aarch64 --target gen-ir
```

The output is `build/aarch64/lira_ir/AArch64.yaml`. The converter prints the
number of instructions, operations, and snippets generated.

## Python

With this repository and LIRA's `python` directory on `PYTHONPATH`:

```bash
PYTHONPATH=.:/path/to/LIRA/python python3 -m utils.asl2lira.main \
  --xml /path/to/ISA_A64_xml_A_profile \
  --output /path/to/AArch64.yaml
```

`--xml` must name the XML directory; `--output` names the LIRA YAML file.

## Scope

The converter covers these groups from the AArch64 branch of LIRA:

| Module | Instruction group |
| --- | --- |
| [`insns_a64.py`](insns_a64.py) | Base integer instructions and shared registration |
| [`insns_fp.py`](insns_fp.py) | Scalar floating point and SIMD/FP loads and stores |
| [`insns_simd.py`](insns_simd.py), [`insns_simd2.py`](insns_simd2.py) | Advanced SIMD integer and crypto |
| [`insns_v8.py`](insns_v8.py) | ARMv8.x general-purpose and system extensions |
| [`insns_sve.py`](insns_sve.py) | SVE |
| [`insns_sme.py`](insns_sme.py) | SME |

With the 2026-06 XML release, it emits 4,138 instructions, 433 operations, 349
snippets, 100 float operations, and 10 integer tables. The IR includes the X,
NZCV, V, FPCR, FPSR, Z, P, FFR, ZA, and SVCR register files, plus environment
functions for effects such as memory and exceptions.

`gen-ir` generates IR only; this directory does not generate a runnable
simulator. The C++ generator does not yet support all emitted operations,
statement kinds, and scalable shapes.

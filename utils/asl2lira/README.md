# AArch64 ASL XML to LIRA IR converter

Converts selected A64 instruction encodings from the Arm machine-readable XML
specification into LIRA IR. The XML supplies encoding fields and constraints;
instruction semantics are implemented in [`insns_a64.py`](insns_a64.py). This is not a
general ASL pseudocode translator.

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

The converter currently covers the A64 base integer instructions registered
in [`insns_a64.py`](insns_a64.py). It emits register files, environment functions,
operations, snippets, and instruction semantics. The `gen-ir` target generates
IR only; this directory does not generate a runnable simulator. A full CMake
build currently requires C++ generator support for operations defined by LIRA
snippets, such as `add_with_carry_32`.

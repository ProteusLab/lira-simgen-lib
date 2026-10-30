# Shared C++ code generation

Generators C++ sources from LIRA IR.

## Getting the LIRA IR

The LIRA IR is generated from the Protea ADL at build time (see
[utils/protea2lira](../utils/protea2lira) for details):

```bash
cmake -B build -DARCH_TARGET=RISC_V -DARCH_SOURCE=Protea
cmake --build build --target gen-ir
```

## Base Operations codegen

Generates `base_ops.hh` / `base_ops.cc` — reference C++ implementations of the LIRA base operations.

```bash
python3 cpp/base_ops.py --ir-path <path/to/LIRA.yaml> --arch-target RISC_V --out-dir <path/to/output-dir>
```

## Snippets codegen

Generates `snippets.hh` / `snippets.cc` — C++ functions for the decode/encode/constraint snippets of all instructions.

```bash
python3 cpp/snippets.py --ir-path <path/to/LIRA.yaml> --arch-target RISC_V --out-dir <path/to/output-dir>
```

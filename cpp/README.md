# Shared C++ code generation

Generators C++ sources from LIRA IR.

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

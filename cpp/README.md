# cpp — shared C++ code generation

Generators for the shared C++ sources (base operations and snippets) from LIRA IR.

## Getting the LIRA IR

The LIRA IR is generated from the Protea ADL at build time (see
[utils/protea2lira](../utils/protea2lira) for details):

```bash
cmake -B build -DARCH_TARGET=RISC_V -DARCH_SOURCE=Protea
cmake --build build --target gen-ir
```

The LIRA IR is written to `build/lira_ir/RISC_V.yaml`.

Both generators take the same arguments:

| Argument | Description |
|---|---|
| `--ir-path` | path to the LIRA IR file (e.g. `build/lira_ir/RISC_V.yaml`) |
| `--arch-target` | target Python package name: `interpreter/Target/<ARCH_TARGET>` (e.g. `RISC_V`) |
| `--out-dir` | directory for the generated files |

## cpp.base_ops

Generates `base_ops.hh` / `base_ops.cc` — C++ implementations of the LIRA base operations
(arithmetic, comparisons, shifts, extensions, ...).

```
python3 cpp/base_ops.py --ir-path build/lira_ir/RISC_V.yaml --arch-target RISC_V --out-dir <out>
```

## cpp.snippets

Generates `snippets.hh` / `snippets.cc` — C++ functions for the decode/encode/constraint
snippets of all instructions.

```
python3 cpp/snippets.py --ir-path build/lira_ir/RISC_V.yaml --arch-target RISC_V --out-dir <out>
```

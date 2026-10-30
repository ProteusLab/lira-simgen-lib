# cpp — shared C++ code generation

Generators for the shared C++ sources (base operations and snippets) from LIRA IR.

## Getting the LIRA IR

Generate the LIRA IR from the native Protea IR first (see
[utils/protea2lira](../utils/protea2lira) for details):

```
python3 utils/protea2lira/main.py --ir-path <native Protea IR> --output RISC_V.yaml
```

Both generators take the same arguments:

| Argument | Description |
|---|---|
| `--ir-path` | path to the LIRA IR file (e.g. `RISC_V.yaml`) |
| `--arch-target` | target Python package name: `interpreter/Target/<ARCH_TARGET>` (e.g. `RISC_V`) |
| `--out-dir` | directory for the generated files |

## cpp.base_ops

Generates `base_ops.hh` / `base_ops.cc` — C++ implementations of the LIRA base operations
(arithmetic, comparisons, shifts, extensions, ...).

```
python3 cpp/base_ops.py --ir-path RISC_V.yaml --arch-target RISC_V --out-dir <out>
```

## cpp.snippets

Generates `snippets.hh` / `snippets.cc` — C++ functions for the decode/encode/constraint
snippets of all instructions.

```
python3 cpp/snippets.py --ir-path RISC_V.yaml --arch-target RISC_V --out-dir <out>
```

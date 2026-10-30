# cpp — shared C++ code generation

Generators for the shared C++ sources (base operations and snippets) from LIRA IR.

## Requirements

- Python >= 3.10
- [Jinja2](https://pypi.org/project/Jinja2/)
- the LIRA python package (e.g. `build/Default-Release/_deps/lira-src/python`)
- a LIRA IR file (generated from Protea at build time by the `gen-ir` target; manually via
  `python3 utils/protea2lira/main.py --ir-path <PIR> --output <LIRA_IR>`)

Both generators take the same arguments:

| Argument | Description |
|---|---|
| `--ir-path` | path to the LIRA IR file (e.g. `build/Default-Release/lira_ir/RISC_V.yaml`) |
| `--arch-target` | target Python package name: `interpreter/Target/<ARCH_TARGET>` (e.g. `RISC_V`) |
| `--out-dir` | directory for the generated files |

Run from the repository root with `PYTHONPATH` including the repository root
and the LIRA python package:

```
PYTHONPATH=$PWD:build/Default-Release/_deps/lira-src/python \
  python3 -m cpp.base_ops \
  --ir-path build/Default-Release/lira_ir/RISC_V.yaml \
  --arch-target RISC_V \
  --out-dir /tmp/opencode/out
```

`python3 -m cpp.snippets` is run the same way with the same arguments.

## cpp.base_ops

Generates `base_ops.hh` / `base_ops.cc` — C++ implementations of the LIRA base operations
(arithmetic, comparisons, shifts, extensions, ...).

## cpp.snippets

Generates `snippets.hh` / `snippets.cc` — C++ functions for the decode/encode/constraint
snippets of all instructions.

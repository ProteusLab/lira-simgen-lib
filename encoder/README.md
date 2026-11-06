# Encoder

Instruction encoder code generation from the LIRA IR.

## Getting the LIRA IR

The encoder consumes the LIRA IR, which is generated at build time from the
architecture description.

For example, from [Protea](utils/protea2lira/main.py) (RISC-V):
```bash
cmake -B build -DARCH_TARGET=RISC_V -DARCH_SOURCE=Protea
cmake --build build --target gen-ir
```

The LIRA IR is written to `build/lira_ir/RISC_V.yaml`.

## Run tool standalone

```bash
python3 encoder/main.py --ir-path <path/to/LIRA.yaml> --arch-target <target-name> --out-dir <path/to/output-dir>
```

## Generate sources

```bash
cmake --preset Default-Release
cmake --build build/Default-Release --target gen-encoder
```

## Build

```bash
cmake --preset Default-Release
cmake --build build/Default-Release --target build-encoder
```

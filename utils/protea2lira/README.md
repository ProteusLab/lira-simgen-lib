# Native Protea IR to LIRA IR converter

Converts the native Protea IR (PIR) into LIRA IR.

## CMake

The `gen-ir` target generates the LIRA IR from the native Protea IR, which is
itself generated from the Protea ADL at build time:

```bash
cmake -B build -DARCH_TARGET=RISC_V -DARCH_SOURCE=Protea
cmake --build build --target gen-ir
```

The LIRA IR is written to `build/lira_ir/RISC_V.yaml`.

## Python3

```bash
python3 utils/protea2lira/main.py --ir-path <path/to/PIR.yaml> --output <path/to/LIRA.yaml>
```

| Argument | Description |
|---|---|
| `--ir-path` | path to the native Protea IR |
| `--output` | path of the generated LIRA IR |



# Interpreter

LIRA-driven generator of a simple C++ interpreter.

**Layout:**

- [Target](Target) — target-specific implementation details.
- [runtime](runtime) — static C++ runtime

## Build

From the repository root:

```bash
cmake --preset Default-Release [OPTIONS]
cmake --build build/Default-Release --target gen-interp   # code generation
cmake --build build/Default-Release --target build-interp # simulator build
```

The generated sources and the interpreter binary are placed into `build/Default-Release/interpreter` (override via `INTERP_OUT_DIR`).

## Options

| Option               | Default                             | Description                                               |
| -------------------- | ----------------------------------- | --------------------------------------------------------- |
| `ARCH_TARGET`      | `RISC_V`                          | Target architecture (`data/${ARCH_TARGET}` directory)   |
| `INTERP_OUT_DIR`   | `${CMAKE_BINARY_DIR}/interpreter` | Directory for the generated interpreter sources           |
| `CMAKE_BUILD_TYPE` | via preset (`Release`)            | Build type (`Release` / `Debug` / `RelWithDebInfo`) |

## Standalone

```bash
python3 interpreter/main.py \
    --ir-path <path/to/lira.yaml> \
    --out-dir <path/to/output-dir>
```

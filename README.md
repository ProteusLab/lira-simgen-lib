# lira-simgen-lib

LIRA-driven simulator generator framework

**Layout:**

- [lib](lib) — the generator library
- [interpreter](interpreter) — C++ interpreter consumer

## Configure and build

```bash
cmake --preset Default-Release -DARCH_TARGET=RISC_V
cmake --build build/Default-Release --target build-interp
```

Available configuration options:

| Option               | Default                  | Description                                               |
| -------------------- | ------------------------ | --------------------------------------------------------- |
| `ARCH_TARGET`      | `RISC_V`               | Target architecture: `RISC_V` or `AArch64` (`data/${ARCH_TARGET}` directory) |
| `CMAKE_BUILD_TYPE` | via preset (`Release`) | Build type (`Release` / `Debug` / `RelWithDebInfo`) |

CMake build presets are defined in [CMakePresets.json](CMakePresets.json) (e.g. `Default-Release`, `Default-Debug`).

## Python install

```bash
pip install --no-deps .
```

Consumers import the library as `lib`.

## Targets

Each target lives in `interpreter/Target/<ARCH_TARGET>` (register-file models,
environment interfaces, `target.cmake` with the IR path and runtime sources)
and `interpreter/runtime/Target/<ARCH_TARGET>` (ELF loader, syscalls, `main`).

- `RISC_V` — RV32I (`data/RISC_V/RV32I.yaml`).
- `AArch64` — A64 base integer instructions, MRS/MSR for NZCV/FPCR/FPSR and
  the scalar v8.x instructions without FP (`data/AArch64/aarch64.yaml`,
  generated in the LIRA repository by
  `python -m archs.aarch64.gen --simgen <path>`). Linux-style
  `exit`/`write` syscalls via `SVC`. The `a64-capi` target builds
  `liba64-capi` (single-instruction execution over host memory) used by the
  LIRA AArch64 tests.

```bash
cmake --preset Default-Release -DARCH_TARGET=AArch64
cmake --build build/Default-Release --target build-interp a64-capi
build/Default-Release/interpreter/interpreter --propagate-exit prog.elf
```

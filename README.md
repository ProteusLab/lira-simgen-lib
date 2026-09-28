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

A table operation (`semantic_table`) is a lookup in a `static constexpr`
copy of the description's table.

A value of a vector statement (shape N > 1) is a `std::array` of N lanes;
lane-wise statements (`op`, `fop`, `env`, `cond_env`) become loops over the
lanes, and `index`, `replicate`, `gather`, `extract_first`, `extend_zero`,
`fold` and shaped register accesses use `interpreter/runtime/lira_vec.hh`.

`fop` statements call the standard float operations of
`interpreter/runtime/lira_fp.hh`, a C++ port of LIRA's reference
(`lira/float_ops.py`: Arm FPU rules, exact rounding in every mode, FZ/FZ16/DN
and exception flags). The FPU controls and flags live in the registers the
description marks with `fpu.*` attributes.

Each target lives in `interpreter/Target/<ARCH_TARGET>` (register-file models,
environment interfaces, `target.cmake` with the IR path and runtime sources)
and `interpreter/runtime/Target/<ARCH_TARGET>` (ELF loader, syscalls, `main`).

- `RISC_V` — RV32I (`data/RISC_V/RV32I.yaml`).
- `AArch64` — A64 base integer instructions, MRS/MSR for NZCV/FPCR/FPSR and
  the scalar v8.x instructions without FP, including exclusives, LSE atomics,
  load-acquire/store-release, barriers and hints, scalar floating point
  and Advanced SIMD (`data/AArch64/aarch64.yaml`,
  generated in the LIRA repository by
  `python -m archs.aarch64.gen --simgen <path>`). Linux-style
  `exit`/`write` syscalls via `SVC`; a misaligned atomic, ordered or
  exclusive access is an Alignment fault that stops the program. MOPS
  (CPY*/SET*) copy or set the whole block in the prologue; copies that may
  overlap behave like memmove. Pointer authentication follows a Linux EL0
  process (48-bit VAs, top byte ignored for data pointers only) with an
  implementation-defined keyed hash as the PAC and fixed keys; a failed
  authentication is a fault (FEAT_FPAC). The
  `a64-capi` target builds
  `liba64-capi` (single-instruction execution over host memory) used by the
  LIRA AArch64 tests.

```bash
cmake --preset Default-Release -DARCH_TARGET=AArch64
cmake --build build/Default-Release --target build-interp a64-capi
build/Default-Release/interpreter/interpreter --propagate-exit prog.elf
```

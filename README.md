# lira-simgen-lib

LIRA-driven simulator generator framework

**Layout:**

- [lib](lib) — the generator library (shared drivers and IR plumbing)
- [cpp](cpp) — shared C++ renderers and code generators (`base_ops.hh/cc`, `snippets.hh/cc`)
- [encoder](encoder) — instruction encoder code generation (`isa.hh`, `encoder.hh/cc`)
- [utils/protea2lira](utils/protea2lira) — native Protea IR (PIR) → LIRA IR converter

## Configure and build

```bash
cmake --preset Default-Release [PROJECT_OPTIONS]
cmake --build build/Default-Release --target build-encoder
```

Available project configuration options:

| Option              | Default                        | Description                                                   |
| ------------------- | ------------------------------ | ------------------------------------------------------------- |
| `ARCH_TARGET`       | *(required)*                   | Target architecture                                           |
| `ARCH_SOURCE`       | *(required)*                   | Architecture description source (`Protea`, `ASL`)             |
| `LIRA_IR_DIR`       | `${CMAKE_BINARY_DIR}/lira_ir`  | Directory for the generated LIRA IR (`RISC_V.yaml`)           |
| `CPP_OUT_DIR`       | `${CMAKE_BINARY_DIR}/cpp`      | Directory for the generated base operation and snippet sources |
| `ENCODER_OUT_DIR`   | `${CMAKE_BINARY_DIR}/encoder`  | Directory for the generated encoder sources                   |
| `CMAKE_BUILD_TYPE`  | via preset (`Release`)         | Build type (`Release` / `Debug` / `RelWithDebInfo`)           |

CMake build presets are defined in [CMakePresets.json](CMakePresets.json) (e.g. `Default-Release`, `Default-Debug`).

## Code-generation targets

The C++ sources are produced by independent generators, each reading the
LIRA IR produced by the converter:

| Target         | Generates                        |
| -------------- | -------------------------------- |
| `gen-ir`       | the LIRA IR                      |
| `gen-base_ops` | `base_ops.hh/cc`                 |
| `gen-snippets` | `snippets.hh/cc`                 |
| `gen-encoder`  | `isa.hh`, `encoder.hh/cc`        |

The IR is generated as part of every target above.

## Build targets

Generated sources land in dedicated directories under the build tree
(`build/Default-Release/{lira_ir,cpp,encoder}`), and the encoder is
packaged as a static library usable on its own:

| Target          | Produces                                             |
| --------------- | ---------------------------------------------------- |
| `base_ops`      | static library from `base_ops.cc`                    |
| `snippets`      | static library from `snippets.cc` (links `base_ops`) |
| `encoder`       | static library from `encoder.cc` (links `snippets`)  |
| `build-encoder` | convenience target for the `encoder` library         |

## Python install

```bash
pip install --no-deps .
```

Consumers import the generator library as `lib`.

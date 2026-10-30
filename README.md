# lira-simgen-lib

LIRA-driven simulator generator framework

**Layout:**

- [lib](lib) — the generator library (shared drivers and IR plumbing)
- [cpp](cpp) — shared C++ renderers and code generators (`base_ops.hh/cc`, `snippets.hh/cc`)
- [decoder](decoder) — instruction decoder code generation (`isa.hh`, `decoder.hh/cc`)
- [encoder](encoder) — instruction encoder code generation (`isa.hh`, `encoder.hh/cc`)
- [interpreter](interpreter) — C++ interpreter consumer (`execute.hh/cc`, `cpu_state.hh/cc`) and its [runtime](interpreter/runtime) support library
- [utils/protea2lira](utils/protea2lira) — native Protea IR (PIR) → LIRA IR converter

## Configure and build

```bash
cmake --preset Default-Release [PROJECT_OPTIONS]
cmake --build build/Default-Release --target build-interp 
```

Available project configuration options:

| Option               | Default                  | Description                                               |
| -------------------- | ------------------------ | --------------------------------------------------------- |
| `ARCH_TARGET`      | *(required)*           | Target architecture |
| `ARCH_SOURCE`      | *(required)*           | Architecture description source (`Protea`, `ASL`) |
| `LIRA_IR_DIR`      | `${CMAKE_BINARY_DIR}/lira_ir` | Directory for the generated LIRA IR (`RISC_V.yaml`) |
| `CPP_OUT_DIR`      | `${CMAKE_BINARY_DIR}/cpp` | Directory for the generated base operation and snippet sources |
| `DECODER_OUT_DIR`  | `${CMAKE_BINARY_DIR}/decoder` | Directory for the generated decoder sources |
| `ENCODER_OUT_DIR`  | `${CMAKE_BINARY_DIR}/encoder` | Directory for the generated encoder sources |
| `INTERP_OUT_DIR`   | `${CMAKE_BINARY_DIR}/interpreter` | Directory for the generated interpreter sources and the interpreter binary |
| `CMAKE_BUILD_TYPE` | via preset (`Release`) | Build type (`Release` / `Debug` / `RelWithDebInfo`) |

CMake build presets are defined in [CMakePresets.json](CMakePresets.json) (e.g. `Default-Release`, `Default-Debug`).

## Code-generation targets

The C++ sources are produced by five independent generators, each reading
the LIRA IR produced by the converter:

| Target          | Generates                                          |
| --------------- | -------------------------------------------------- |
| `gen-ir`        | the LIRA IR                           |
| `gen-base_ops`  | `base_ops.hh/cc`                                   |
| `gen-snippets`  | `snippets.hh/cc`                                   |
| `gen-decoder`   | `isa.hh`, `decoder.hh/cc`                          |
| `gen-encoder`   | `isa.hh`, `encoder.hh/cc`                          |
| `gen-interp`    | `execute.hh/cc`, `cpu_state.hh/cc`                 |

The IR is generated as part of every target above. 
`isa.hh` is header-only and generated independently by both the decoder and the encoder: each
component writes an identical copy into its own output directory.

## Build targets

Generated sources land in dedicated directories under the build tree
(`build/Default-Release/{lira_ir,cpp,decoder,encoder,interpreter}`), and the
decoder/encoder are packaged as static libraries usable on their own:

| Target          | Produces                                                 |
| --------------- | -------------------------------------------------------- |
| `base_ops`      | static library from `base_ops.cc`                        |
| `snippets`      | static library from `snippets.cc` (links `base_ops`)     |
| `decoder`       | static library from `decoder.cc` (links `snippets`)      |
| `encoder`       | static library from `encoder.cc` (links `snippets`)      |
| `runtime`       | static runtime library (engine, ELF loader, CPU state extensions) |
| `build-decoder` | convenience target for the `decoder` library             |
| `build-encoder` | convenience target for the `encoder` library             |
| `build-runtime` | convenience target for the `runtime` library             |
| `build-interp`  | the compiled `interpreter` executable                    |

## Python install

```bash
pip install --no-deps .
```

Consumers import the generator library as `lib` and the interpreter
consumer as `interpreter`.

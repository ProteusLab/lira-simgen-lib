# lira-simgen-lib/encoder

Instruction encoder code generation from the LIRA IR.

## Getting the LIRA IR

The encoder consumes the LIRA IR, which is generated at build time from the
architecture description (Protea):

    cmake -B build -DARCH_TARGET=RISC_V -DARCH_SOURCE=Protea
    cmake --build build --target gen-ir

The IR lands in `build/lira_ir/RISC_V.yaml`. See `utils/protea2lira` for the
standalone converter.

## Usage

    python3 encoder/main.py --ir-path build/lira_ir/RISC_V.yaml --arch-target RISC_V --out-dir <dir>

| Argument        | Meaning                                  |
|-----------------|------------------------------------------|
| `--ir-path`     | path to the LIRA IR                      |
| `--arch-target` | target model package under `lib/Target/` |
| `--out-dir`     | directory for the generated sources      |

## Generated sources

`encoder.hh` declares `prot::encoder::Word` (the machine word) and the
`encode_<name>` functions; `encoder.cc` defines them. The encoder is
self-contained and includes no generated header from other tools.

## Build

    cmake --preset Default-Release
    cmake --build build/Default-Release --target build-encoder

`gen-encoder` regenerates the sources, `build-encoder` builds the `encoder`
static library. It links against `snippets` for the encode snippet functions.

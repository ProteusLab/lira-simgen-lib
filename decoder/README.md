# lira-simgen-lib/decoder

Instruction decoder code generation from the LIRA IR.

## Getting the LIRA IR

The decoder consumes the LIRA IR, which is generated at build time from the
architecture description (Protea):

    cmake -B build -DARCH_TARGET=RISC_V -DARCH_SOURCE=Protea
    cmake --build build --target gen-ir

The IR lands in `build/lira_ir/RISC_V.yaml`. See `utils/protea2lira` for the
standalone converter.

## Usage

    python3 decoder/main.py --ir-path build/lira_ir/RISC_V.yaml --arch-target RISC_V --out-dir <dir>

| Argument        | Meaning                                  |
|-----------------|------------------------------------------|
| `--ir-path`     | path to the LIRA IR                      |
| `--arch-target` | target model package under `lib/Target/` |
| `--out-dir`     | directory for the generated sources      |

## Generated sources

`decoder.hh` declares the instruction vocabulary (`prot::isa`: `Word`,
`Opcode`, `Instruction`, `getILen`) and `prot::decoder::decode`;
`decoder.cc` implements the decode: constraint match and operand extraction.

## Build

    cmake --preset Default-Release
    cmake --build build/Default-Release --target build-decoder

`gen-decoder` regenerates the sources, `build-decoder` builds the `decoder`
static library. It links against `snippets` for the constraint and decode
snippet functions.

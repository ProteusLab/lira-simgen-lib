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

| Option               | Default                             | Description                                               |
| -------------------- | ----------------------------------- | --------------------------------------------------------- |
| `ARCH_TARGET`      | `RISC_V`                          | Target architecture (`data/${ARCH_TARGET}` directory)   |
| `CMAKE_BUILD_TYPE` | via preset (`Release`)            | Build type (`Release` / `Debug` / `RelWithDebInfo`) |

CMake build presets are defined in [CMakePresets.json](CMakePresets.json) (e.g. `Default-Release`, `Default-Debug`).

## Python install

```bash
pip install --no-deps .
```

Consumers import the library as `lib`.

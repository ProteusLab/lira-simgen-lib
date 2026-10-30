# utils/protea2lira — native Protea IR to LIRA IR converter

Converts the native Protea IR (PIR) into LIRA IR.

```
python3 utils/protea2lira/main.py --ir-path <native Protea IR> --output <LIRA IR>
```

| Argument | Description |
|---|---|
| `--ir-path` | path to the native Protea IR (`IR.yaml`, produced by Protea's `protea_irgen` target) |
| `--output` | path of the generated LIRA IR (e.g. `RISC_V.yaml`) |

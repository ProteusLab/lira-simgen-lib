class OperandType:
    VOID = "void"
    BOOL = "bool"

    U8 = "uint8_t"
    I8 = "int8_t"

    U16 = "uint16_t"
    I16 = "int16_t"

    U32 = "uint32_t"
    I32 = "int32_t"

    U64 = "uint64_t"
    I64 = "int64_t"

    U128 = "uint128_t"
    I128 = "int128_t"

    _STANDARD_WIDTHS = [1, 8, 16, 32, 64, 128]
    _WIDTH_TYPES = {
        1: (BOOL, BOOL),
        8: (U8, I8),
        16: (U16, I16),
        32: (U32, I32),
        64: (U64, I64),
        128: (U128, I128),
    }

    @classmethod
    def gen(cls, width: int, signed: bool = False) -> str:
        return cls._WIDTH_TYPES[cls.bits(width)][1 if signed else 0]

    @classmethod
    def bits(cls, width: int) -> int:
        return next(s for s in cls._STANDARD_WIDTHS if s >= width)

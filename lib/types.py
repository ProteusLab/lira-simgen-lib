# lira-simgen-lib/simgen/types.py


class OperandType:
    _STANDARD_WIDTHS = [1, 8, 16, 32, 64, 128, 256]

    @classmethod
    def gen(cls, width: int, signed: bool = False) -> str:
        rounded = cls.bits(width)
        if rounded == 1:
            return "bool"
        prefix = "" if signed else "u"
        return f"{prefix}int{rounded}_t"

    @classmethod
    def bits(cls, width: int) -> int:
        return next(s for s in cls._STANDARD_WIDTHS if s >= width)

    @classmethod
    def is_exact(cls, width: int) -> bool:
        """True if the C++ type holds exactly `width` bits (no masking needed)."""
        return width != 1 and width in cls._STANDARD_WIDTHS

    @classmethod
    def literal(cls, value: int, width: int) -> str:
        """C++ literal for an unsigned constant of the given width."""
        assert value >> 128 == 0, f"no C++ literal for {value:#x}"
        if width > 64 and value >> 64:
            hi, lo = value >> 64, value & ((1 << 64) - 1)
            return f"((uint128_t){hi:#x}ULL << 64 | {lo:#x}ULL)"
        return f"{value}ULL" if value > 0x7FFFFFFF else str(value)

    @classmethod
    def tuple(cls, widths) -> str:
        """Return type for one or several values."""
        if len(widths) == 1:
            return cls.gen(widths[0])
        return f"std::tuple<{', '.join(cls.gen(w) for w in widths)}>"

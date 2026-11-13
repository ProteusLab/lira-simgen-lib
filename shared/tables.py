"""Lower LIRA tables to C++ declarations."""

from lira.arch import TableInt, TableStr

from shared import cpp
from shared.types import OperandType


def compile_table(
    table: TableInt | TableStr,
    *,
    name: str | None = None,
    width: int | None = None,
    static: bool = False,
) -> str:
    """Define a table, using the consuming operation's width for integer entries."""
    if isinstance(table, TableInt):
        if width is None:
            raise ValueError(f"Integer table {table.name} needs an element width")
        element_type = OperandType.gen(width)
        entries = (cpp.integer_literal(value % (1 << width)) for value in table.values)
    else:
        element_type = "std::string_view"
        entries = map(cpp.string_view_literal, table.values)
    return cpp.constexpr_array(name or table.name, element_type, entries, static=static)

"""C++ code objects and rendering helpers."""

from dataclasses import dataclass


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.split("\n"))


@dataclass
class Statement:
    """A fragment of C++ body text. Subclasses may carry their own structure."""

    text: str

    def render(self, *, indent: int = 0) -> str:
        """Render the fragment with indent spaces before each nonempty line."""
        return _indent(self.text, indent)


@dataclass(frozen=True)
class NamedValue:
    name: str
    type: str

    def __str__(self) -> str:
        return self.name

    def declaration(self) -> str:
        return f"{self.type} {self.name}"


@dataclass
class Function:
    name: str
    return_type: str
    parameters: tuple[NamedValue, ...]
    body: list[Statement]

    def _signature(self) -> str:
        params = ", ".join(param.declaration() for param in self.parameters)
        return f"{self.return_type} {self.name}({params})"

    def declaration(self, *, indent: int = 0) -> str:
        return _indent(self._signature() + ";", indent)

    def definition(self, *, indent: int = 0) -> str:
        lines = [_indent(self._signature() + " {", indent)]
        lines.extend(stmt.render(indent=indent + 2) for stmt in self.body)
        lines.append(_indent("}", indent))
        return "\n".join(lines)

    def call(self, *arguments: str) -> str:
        return f"{self.name}({', '.join(arguments)})"


@dataclass
class Struct:
    name: str
    fields: tuple[NamedValue, ...]

    def definition(self, *, indent: int = 0) -> str:
        members = "\n".join(f"  {field.declaration()};" for field in self.fields)
        return _indent(f"struct {self.name} {{\n{members}\n}};", indent)

    def initializer(self, **fields: str) -> str:
        unknown = fields.keys() - {field.name for field in self.fields}
        if unknown:
            raise ValueError(f"Unknown {self.name} fields: {', '.join(sorted(unknown))}")
        members = ", ".join(
            f".{field.name} = {fields[field.name]}"
            for field in self.fields
            if field.name in fields
        )
        return f"{self.name}{{{members}}}"


def integer_literal(value: int) -> str:
    if 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        return f"{value}ULL"
    upper, lower = divmod(value, 1 << 64)
    return f"((uint128_t{{{upper}ULL}} << 64) | {lower}ULL)"

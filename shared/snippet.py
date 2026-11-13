"""LIRA value types and snippet slots."""

from dataclasses import dataclass

from lira.arch import Snippet
from lira.ir import Shape


@dataclass(frozen=True)
class Value:
    name: str
    width: int
    shape: Shape


@dataclass
class SnippetInfo:
    values: dict[str, Value]
    inputs: dict[int, Value]
    outputs: dict[int, Value]


def analyze_snippet(snippet: Snippet) -> SnippetInfo:
    """Resolve values and collect input and output slots in index order."""
    values = {}
    inputs = {}
    outputs = {}
    for stmt in snippet.seq.stmts:
        args = [values[name] for name in stmt.inputs]
        shape = Shape(1, None) if stmt.kind == "fold" else stmt.shape
        results = [
            Value(name, width, shape)
            for name, width in zip(stmt.outputs, stmt.outputs_types, strict=True)
        ]
        for value in results:
            if value.name in values:
                raise ValueError(f"{snippet.name}: repeated definition of {value.name}")
            values[value.name] = value

        if stmt.kind == "input":
            (value,) = results
            index = int(stmt.specifier)
            previous = inputs.setdefault(index, value)
            if index < 0 or (previous.width, previous.shape) != (value.width, value.shape):
                raise ValueError(f"{snippet.name}: invalid input {index}")
        elif stmt.kind == "output":
            (value,) = args
            index = int(stmt.specifier)
            if index < 0 or index in outputs:
                raise ValueError(f"{snippet.name}: invalid output {index}")
            outputs[index] = value

    return SnippetInfo(values, dict(sorted(inputs.items())), dict(sorted(outputs.items())))

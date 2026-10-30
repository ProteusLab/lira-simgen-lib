# lira-simgen-lib/lib/snippet.py

from enum import Enum


class SnippetKind(Enum):
    """Role of a snippet in the instruction encoding."""

    DECODE = "decode"
    ENCODE = "encode"
    CONSTRAINT = "constraint"

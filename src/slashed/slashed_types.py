"""Slashed types."""

from typing import Literal


CompletionKind = Literal[
    "command",
    "command-arg",
    "route",
    "file",
    "directory",
    "python",
    "yaml",
    "json",
    "markdown",
    "text",
    "tool",
    "path",
    "env",
    "choice",
    "keyword",
]

"""Slashed types."""

from __future__ import annotations

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

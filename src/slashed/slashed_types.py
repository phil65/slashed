"""Slashed types."""

from __future__ import annotations

from typing import Literal


CompletionKind = Literal["command", "file", "tool", "path", "env", "choice"]

"""Textual integration for Slashed."""

from __future__ import annotations

from slashed.textual_adapter.app import (
    SlashedApp,
    TextualOutputWriter,
)
from slashed.textual_adapter.suggester import SlashedSuggester

__all__ = [
    "SlashedApp",
    "SlashedSuggester",
    "TextualOutputWriter",
]

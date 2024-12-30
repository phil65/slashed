"""Textual integration for Slashed."""

from __future__ import annotations

from slashed.textual_adapter.app import (
    SlashedApp,
    TextualOutputWriter,
)
from slashed.textual_adapter.suggester import SlashedSuggester
from slashed.textual_adapter.command_input import CommandInput
from slashed.textual_adapter.command_textarea import CommandTextArea

__all__ = [
    "CommandInput",
    "CommandTextArea",
    "SlashedApp",
    "SlashedSuggester",
    "TextualOutputWriter",
]

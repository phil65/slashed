"""Command system for Slashed - a slash command system with autocompletion."""

from __future__ import annotations

from slashed.base import (
    BaseCommand,
    Command,
    CommandContext,
    ParsedCommand,
    ParsedCommandArgs,
    parse_command,
)
from slashed.completion import CompletionContext, CompletionItem, CompletionProvider
from slashed.completers import (
    ChainedCompleter,
    ChoiceCompleter,
    EnvVarCompleter,
    KeywordCompleter,
    MultiValueCompleter,
    PathCompleter,
)
from slashed.exceptions import CommandError, ExitCommandError
from slashed.output import DefaultOutputWriter
from slashed.store import CommandStore


__version__ = "0.4.2"

__all__ = [
    # Core
    "BaseCommand",
    # Completers
    "ChainedCompleter",
    "ChoiceCompleter",
    "Command",
    "CommandContext",
    "CommandError",
    "CommandStore",
    # Completion
    "CompletionContext",
    "CompletionItem",
    "CompletionProvider",
    "DefaultOutputWriter",
    "EnvVarCompleter",
    "ExitCommandError",
    "KeywordCompleter",
    "MultiValueCompleter",
    "ParsedCommand",
    "ParsedCommandArgs",
    "PathCompleter",
    "parse_command",
]

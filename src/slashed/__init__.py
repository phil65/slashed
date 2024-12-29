"""Command system for Slashed - a slash command system with autocompletion."""

from __future__ import annotations

from slashed.base import (
    BaseCommand,
    Command,
    CommandContext,
    OutputWriter,
    ParsedCommand,
    ParsedCommandArgs,
    parse_command,
)
from slashed.commands import SlashedCommand
from slashed.completion import CompletionContext, CompletionItem, CompletionProvider
from slashed.completers import (
    CallbackCompleter,
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
from slashed.registry import CommandRegistry


__version__ = "0.7.2"

__all__ = [  # noqa: RUF022
    # Core
    "BaseCommand",
    "Command",
    "CommandContext",
    "CommandError",
    "CommandStore",
    "OutputWriter",
    "ParsedCommand",
    "ParsedCommandArgs",
    "SlashedCommand",
    "parse_command",
    "CommandRegistry",
    # Completion
    "CompletionContext",
    "CompletionItem",
    "CompletionProvider",
    # Completers
    "CallbackCompleter",
    "ChainedCompleter",
    "ChoiceCompleter",
    "EnvVarCompleter",
    "KeywordCompleter",
    "MultiValueCompleter",
    "PathCompleter",
    # Output
    "DefaultOutputWriter",
    # Exceptions
    "ExitCommandError",
]

"""Slashed: main package.

Slash commands and autocompletions.
"""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("slashed")
__title__ = "Slashed"

__author__ = "Philipp Temminghoff"
__author_email__ = "philipptemminghoff@googlemail.com"
__copyright__ = "Copyright (c) 2024 Philipp Temminghoff"
__license__ = "MIT"
__url__ = "https://github.com/phil65/slashed"

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
from slashed.router import CommandRouter, Route, RouteInfo, ParsedRoute
from slashed.exceptions import CommandError, ExitCommandError
from slashed.output import (
    DefaultOutputWriter,
    QueueOutputWriter,
    CallbackOutputWriter,
    TransformOutputWriter,
)
from slashed.store import CommandStore
from slashed.registry import CommandRegistry


__all__ = [  # noqa: RUF022
    # Core
    "BaseCommand",
    "Command",
    "CommandContext",
    "CommandRouter",
    "Route",
    "RouteInfo",
    "ParsedRoute",
    "CommandError",
    "CommandStore",
    "OutputWriter",
    "ParsedCommand",
    "ParsedCommandArgs",
    "SlashedCommand",
    "parse_command",
    "CommandRegistry",
    "CallbackOutputWriter",
    "QueueOutputWriter",
    "TransformOutputWriter",
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
    # Version
    "__version__",
]

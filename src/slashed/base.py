"""Base interfaces for the command system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
import shlex
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from slashed.completion import CompletionProvider
from slashed.exceptions import CommandError


if TYPE_CHECKING:
    from collections.abc import Awaitable

    from slashed.store import CommandStore

T = TypeVar("T")


class OutputWriter(Protocol):
    """Interface for command output."""

    async def print(self, message: str) -> None:
        """Write a message to output."""
        ...


@dataclass
class CommandContext[T]:
    """Context passed to command handlers."""

    output: OutputWriter
    data: T
    command_store: CommandStore
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCommandArgs:
    """Arguments parsed from a command string."""

    args: list[str]
    kwargs: dict[str, str]


@dataclass
class ParsedCommand:
    """Complete parsed command."""

    name: str
    args: ParsedCommandArgs


type ExecuteFunc = Callable[[CommandContext, list[str], dict[str, str]], Awaitable[None]]


class BaseCommand(ABC):
    """Abstract base class for commands."""

    name: str
    """Command name"""

    description: str
    """Command description"""

    category: str
    """Command category"""

    usage: str | None
    """Command usage"""

    _help_text: str | None
    """Optional help text"""

    def get_completer(self) -> CompletionProvider | None:
        """Get completion provider for this command.

        Returns:
            CompletionProvider if command supports completion, None otherwise
        """
        return None

    def format_usage(self) -> str | None:
        """Format usage string."""
        if not self.usage:
            return None
        return f"Usage: /{self.name} {self.usage}"

    @property
    def help_text(self) -> str:
        """Get help text, falling back to description if not set."""
        return self._help_text or self.description

    @abstractmethod
    async def execute(self, ctx: CommandContext, args: list[str], kwargs: dict[str, str]):
        """Execute the command with parsed arguments."""
        ...


class Command(BaseCommand):
    """Concrete command that can be created directly."""

    def __init__(
        self,
        name: str,
        description: str,
        execute_func: ExecuteFunc,
        category: str = "general",
        usage: str | None = None,
        help_text: str | None = None,
        completer: CompletionProvider | Callable[[], CompletionProvider] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.category = category
        self.usage = usage
        self._help_text = help_text
        self._execute_func = execute_func
        self._completer = completer

    async def execute(
        self,
        ctx: CommandContext,
        args: list[str] | None = None,
        kwargs: dict[str, str] | None = None,
    ) -> None:
        """Execute the command using provided function."""
        await self._execute_func(ctx, args or [], kwargs or {})

    def get_completer(self) -> CompletionProvider | None:
        """Get completion provider."""
        match self._completer:
            case None:
                return None
            case CompletionProvider() as completer:
                return completer
            case Callable() as factory:
                return factory()
            case _:
                typ = type(self._completer)
                msg = f"Completer must be CompletionProvider or callable, not {typ}"
                raise TypeError(msg)


def parse_command(cmd_str: str) -> ParsedCommand:
    """Parse command string into name and arguments.

    Args:
        cmd_str: Command string without leading slash

    Returns:
        Parsed command with name and arguments

    Raises:
        CommandError: If command syntax is invalid
    """
    try:
        parts = shlex.split(cmd_str)
    except ValueError as e:
        msg = f"Invalid command syntax: {e}"
        raise CommandError(msg) from e

    if not parts:
        msg = "Empty command"
        raise CommandError(msg)

    name = parts[0]
    args = []
    kwargs = {}

    i = 1
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            if i + 1 < len(parts):
                kwargs[part[2:]] = parts[i + 1]
                i += 2
            else:
                msg = f"Missing value for argument: {part}"
                raise CommandError(msg)
        else:
            args.append(part)
            i += 1
    args_obj = ParsedCommandArgs(args=args, kwargs=kwargs)
    return ParsedCommand(name=name, args=args_obj)

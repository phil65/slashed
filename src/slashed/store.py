"""Command store implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from slashed.base import CommandContext, OutputWriter, parse_command
from slashed.completion import CompletionContext
from slashed.exceptions import CommandError
from slashed.log import get_logger
from slashed.output import DefaultOutputWriter


try:
    from upath import UPath as Path
except ImportError:
    from pathlib import Path

if TYPE_CHECKING:
    import os

    from prompt_toolkit.document import Document

    from slashed.base import BaseCommand
    from slashed.commands import SlashedCommand


T = TypeVar("T")
logger = get_logger(__name__)


class CommandStore:
    """Central store for command management and history."""

    def __init__(self, history_file: str | os.PathLike[str] | None = None):
        """Initialize command store.

        Args:
            history_file: Optional path to history file
        """
        self._commands: dict[str, BaseCommand] = {}
        self._command_history: list[str] = []
        self._history_path = Path(history_file) if history_file else None
        if self._history_path:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize command store and load history."""
        try:
            if self._history_path and self._history_path.exists():
                self._command_history = self._history_path.read_text().splitlines()
        except Exception:
            logger.exception("Failed to load command history")
            self._command_history = []

        # Register default commands
        self.register_builtin_commands()

    def add_to_history(self, command: str):
        """Add command to history."""
        if not command.strip():
            return

        self._command_history.append(command)
        if self._history_path:
            self._history_path.write_text("\n".join(self._command_history))

    def get_history(
        self, limit: int | None = None, newest_first: bool = True
    ) -> list[str]:
        """Get command history."""
        history = self._command_history
        if newest_first:
            history = history[::-1]
        return history[:limit] if limit else history

    def create_context(
        self,
        data: T,
        output_writer: OutputWriter | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommandContext[T]:
        """Create a command execution context.

        Args:
            data: Custom context data
            output_writer: Optional custom output writer
            metadata: Additional metadata

        Returns:
            Command execution context
        """
        writer = output_writer or DefaultOutputWriter()
        meta = metadata or {}
        return CommandContext(output=writer, data=data, command_store=self, metadata=meta)

    def create_completion_context(
        self,
        document: Document,
        command_context: CommandContext | None = None,
    ) -> CompletionContext:
        """Create a completion context."""
        return CompletionContext(document, command_context)

    def register_command(self, command: type[SlashedCommand] | BaseCommand) -> None:
        """Register a new command.

        Args:
            command: Command class (SlashedCommand subclass) or command instance

        Raises:
            ValueError: If command with same name exists
        """
        # If given a class, instantiate it
        if isinstance(command, type):
            command = command()

        if command.name in self._commands:
            msg = f"Command '{command.name}' already registered"
            raise ValueError(msg)

        self._commands[command.name] = command
        logger.debug("Registered command: %s", command.name)

    def unregister_command(self, name: str):
        """Remove a command.

        Args:
            name: Name of command to remove
        """
        if name in self._commands:
            del self._commands[name]
            logger.debug("Unregistered command: %s", name)

    def get_command(self, name: str) -> BaseCommand | None:
        """Get command by name.

        Args:
            name: Name of command to get

        Returns:
            Command if found, None otherwise
        """
        return self._commands.get(name)

    def list_commands(
        self,
        category: str | None = None,
    ) -> list[BaseCommand]:
        """List all commands, optionally filtered by category.

        Args:
            category: Optional category to filter by

        Returns:
            List of commands
        """
        if category:
            return [cmd for cmd in self._commands.values() if cmd.category == category]
        return list(self._commands.values())

    def get_categories(self) -> list[str]:
        """Get list of available command categories.

        Returns:
            Sorted list of unique categories
        """
        return sorted({cmd.category for cmd in self._commands.values()})

    def get_commands_by_category(self) -> dict[str, list[BaseCommand]]:
        """Get commands grouped by category.

        Returns:
            Dict mapping categories to lists of commands
        """
        result: dict[str, list[BaseCommand]] = {}
        for cmd in self._commands.values():
            result.setdefault(cmd.category, []).append(cmd)
        return result

    async def execute_command(self, command_str: str, ctx: CommandContext):
        """Execute a command from string input.

        Args:
            command_str: Full command string (without leading slash)
            ctx: Command execution context

        Raises:
            CommandError: If command parsing or execution fails
        """
        self.add_to_history(command_str)
        try:
            # Parse the command string
            parsed = parse_command(command_str)

            # Get the command
            command = self.get_command(parsed.name)
            if not command:
                msg = f"Unknown command: {parsed.name}"
                raise CommandError(msg)  # noqa: TRY301

            msg = "Executing command: %s (args=%s, kwargs=%s)"
            logger.debug(msg, parsed.name, parsed.args.args, parsed.args.kwargs)
            # Execute it
            await command.execute(ctx, parsed.args.args, parsed.args.kwargs)

        except CommandError:
            raise
        except Exception as e:
            msg = f"Command execution failed: {e}"
            raise CommandError(msg) from e

    async def execute_command_with_context(
        self,
        command_str: str,
        context: Any,
        output_writer: OutputWriter | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Execute a command with a custom context."""
        ctx = self.create_context(
            context,
            output_writer=output_writer,
            metadata=metadata,
        )
        await self.execute_command(command_str, ctx)

    def register_builtin_commands(self):
        """Register default system commands."""
        from slashed.builtin import get_builtin_commands

        logger.debug("Registering builtin commands")
        for command in get_builtin_commands():
            self.register_command(command)

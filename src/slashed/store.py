"""Command store implementation."""

from __future__ import annotations

from importlib import import_module
import inspect
from typing import TYPE_CHECKING, Any, TypeVar

from psygnal import Signal
from psygnal.containers import EventedDict

from slashed.base import (
    BaseCommand,
    Command,
    CommandContext,
    ExecuteFunc,
    OutputWriter,
    parse_command,
)
from slashed.builtin import get_system_commands
from slashed.completion import CompletionContext, CompletionProvider
from slashed.context import ContextRegistry
from slashed.events import CommandExecutedEvent
from slashed.exceptions import CommandError
from slashed.log import get_logger
from slashed.output import (
    CallbackOutputWriter,
    DefaultOutputWriter,
    SignalingOutputWriter,
)


try:
    from upath import UPath as Path
except ImportError:
    from pathlib import Path

if TYPE_CHECKING:
    from collections.abc import Callable
    import os

    from prompt_toolkit.document import Document
    from psygnal.containers._evented_dict import DictEvents

    from slashed.commands import SlashedCommand


TContextData = TypeVar("TContextData")
logger = get_logger(__name__)
TCommandFunc = TypeVar("TCommandFunc", bound=ExecuteFunc)


class CommandStore:
    """Central store for command management and history."""

    command_executed = Signal(CommandExecutedEvent)
    output = Signal(str)

    def __init__(
        self,
        history_file: str | os.PathLike[str] | None = None,
        *,
        enable_system_commands: bool = False,
    ):
        """Initialize command store.

        Args:
            history_file: Optional path to history file
            enable_system_commands: Whether to enable system execution commands.
                                  Disabled by default for security.
        """
        self._commands = EventedDict[str, BaseCommand]()
        self._contexts = ContextRegistry()
        self._command_history: list[str] = []
        self._history_path = Path(history_file) if history_file else None
        self._enable_system_commands = enable_system_commands
        self._initialized = False
        if self._history_path:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def command_events(self) -> DictEvents:
        return self._commands.events

    @property
    def context_events(self) -> DictEvents:
        return self._contexts._contexts.events

    def _initialize_sync(self):
        """Initialize the store synchronously."""
        if self._initialized:
            return

        # Load history
        try:
            if self._history_path and self._history_path.exists():
                self._command_history = self._history_path.read_text().splitlines()
        except Exception:
            logger.exception("Failed to load command history")
            self._command_history = []

        # Register commands
        self.register_builtin_commands()
        self._initialized = True

    async def initialize(self):
        """Initialize the store (async wrapper for backward compatibility)."""
        self._initialize_sync()

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

    def create_context[TContextData](
        self,
        data: TContextData | None,
        output_writer: OutputWriter | Callable[..., Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommandContext[TContextData]:
        """Create a command execution context.

        Args:
            data: Custom context data
            output_writer: Optional custom output writer
            metadata: Additional metadata

        Returns:
            Command execution context
        """
        if callable(output_writer):
            output_writer = CallbackOutputWriter(output_writer)
        base_writer = output_writer or DefaultOutputWriter()
        writer = SignalingOutputWriter(self.output, base_writer)
        meta = metadata or {}
        return CommandContext(output=writer, data=data, command_store=self, metadata=meta)

    def create_completion_context(
        self,
        document: Document,
        command_context: CommandContext[TContextData] | None = None,
    ) -> CompletionContext[TContextData]:
        """Create a completion context."""
        return CompletionContext(document, command_context)

    # Context management methods
    def register_context(
        self,
        data: object,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a typed context.

        Example:
            ```python
            @dataclass
            class DBContext:
                connection: str
                timeout: int = 30

            store = CommandStore()
            store.register_context(DBContext("mysql://..."))
            ```
        """
        self._contexts.register(data, metadata)

    def get_context[T](self, context_type: type[T]) -> T:
        """Get a typed context.

        Example:
            ```python
            db_ctx = store.get_context(DBContext)
            # db_ctx is properly typed as DBContext
            ```
        """
        return self._contexts.get(context_type)

    def unregister_context(self, context_type: type) -> None:
        """Unregister a context type."""
        self._contexts.unregister(context_type)

    async def execute_command_auto(
        self,
        command_str: str,
        fallback_context: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Execute command with automatic context matching.

        Args:
            command_str: Command to execute
            fallback_context: Optional context to use if no match found
            metadata: Additional metadata for context

        Example:
            ```python
            # Will automatically use DBContext for database commands
            # and UIContext for UI commands
            await store.execute_command_auto("/query select * from users")
            ```

        Raises:
            CommandError: If no matching context is found and no fallback provided
        """
        parsed = parse_command(command_str)
        command = self.get_command(parsed.name)
        if not command:
            msg = f"Unknown command: {parsed.name}"
            raise CommandError(msg)

        # Try to find matching context
        if reg := self._contexts.match_command(command):
            ctx: CommandContext[Any] = self.create_context(
                reg.data, metadata=reg.metadata
            )
        elif fallback_context is not None:
            ctx = self.create_context(fallback_context, metadata=metadata)
        else:
            msg = f"No matching context found for command {command.name}"
            raise CommandError(msg)

        await self.execute_command(command_str, ctx)

    def register_command(self, command: type[SlashedCommand] | BaseCommand):
        """Register a new command.

        Args:
            command: Command class (SlashedCommand subclass) or command instance

        Raises:
            ValueError: If command with same name exists
        """
        # If given a class, instantiate it
        if isinstance(command, type):
            command = command()

        if not command.is_available():
            return
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

    def list_commands(self, category: str | None = None) -> list[BaseCommand]:
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

    async def execute_command(self, command_str: str, ctx: CommandContext[TContextData]):
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

            # Check for --help flag, but only handle it if command doesn't use it
            if "help" in parsed.args.kwargs:
                # Check command signature via inspect
                sig = inspect.signature(command.execute)
                help_param = next(
                    (p for p in sig.parameters.items() if p[0] == "help"), None
                )

                # Only show our help if command doesn't handle help parameter
                if not help_param:
                    sections = [
                        f"Command: /{command.name}",
                        f"Category: {command.category}",
                        "",
                        "Description:",
                        command.description,
                        "",
                    ]
                    if command.usage:
                        sections.extend([
                            "Usage:",
                            f"/{command.name} {command.usage}",
                            "",
                        ])
                    if command.help_text:
                        sections.extend(["Help:", command.help_text])
                    await ctx.output.print("\n".join(sections))
                    return

            msg = "Executing command: %s (args=%s, kwargs=%s)"
            logger.debug(msg, parsed.name, parsed.args.args, parsed.args.kwargs)
            # Execute it with all args, letting command handle help if it wants to
            await command.execute(ctx, parsed.args.args, parsed.args.kwargs)
            self.command_executed.emit(
                CommandExecutedEvent(
                    command=command_str, context=ctx, success=True, error=None
                )
            )
        except CommandError:
            raise
        except Exception as e:
            msg = f"Command execution failed: {e}"
            self.command_executed.emit(
                CommandExecutedEvent(
                    command=command_str,
                    context=ctx,
                    success=False,
                    error=e,
                )
            )
            raise CommandError(msg) from e

    async def execute_command_with_context[T](
        self,
        command_str: str,
        context: T | None = None,  # type: ignore[type-var]
        output_writer: OutputWriter | Callable[..., Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Execute a command with a custom context.

        Args:
            command_str: Command string to execute (without leading slash)
            context: Custom context data
            output_writer: Optional custom output writer
            metadata: Additional metadata
        """
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

        # System commands only if enabled
        if self._enable_system_commands:
            for command in get_system_commands():
                self.register_command(command)

    def add_command(
        self,
        name: str,
        fn: str | ExecuteFunc,
        *,
        description: str | None = None,
        category: str = "general",
        usage: str | None = None,
        help_text: str | None = None,
        completer: str
        | CompletionProvider
        | Callable[[], CompletionProvider]
        | None = None,
        condition: Callable[[], bool] | None = None,
    ) -> None:
        """Add a command with flexible configuration options.

        Args:
            name: Command name
            fn: Import path (str) or callable for command execution
            description: Command description (defaults to fn's docstring)
            category: Command category
            usage: Optional usage string
            help_text: Optional help text
            completer: Import path, completion provider, or factory callable
            condition: Optional function to check if command is available
        """
        # Import fn if string
        if isinstance(fn, str):
            try:
                module_path, attr_name = fn.rsplit(".", 1)
                module = import_module(module_path)
                fn_obj: ExecuteFunc = getattr(module, attr_name)
            except Exception as e:
                msg = f"Failed to import fn function from {fn}: {e}"
                raise ValueError(msg) from e
        else:
            fn_obj = fn
        # Import completer if string
        if isinstance(completer, str):
            try:
                module_path, attr_name = completer.rsplit(".", 1)
                module = import_module(module_path)
                completer_obj = getattr(module, attr_name)
            except Exception as e:
                msg = f"Failed to import completer from {completer}: {e}"
                raise ValueError(msg) from e
        else:
            completer_obj = completer
        # Use docstring as description if not provided
        if description is None and callable(fn_obj):
            description = fn_obj.__doc__ or "No description"

        # Create and register command
        command = Command(
            name=name,
            description=description or "No description",
            execute_func=fn_obj,
            category=category,
            usage=usage,
            help_text=help_text,
            completer=completer_obj,
            condition=condition,
        )
        self.register_command(command)

    def command(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        category: str = "general",
        usage: str | None = None,
        help_text: str | None = None,
        completer: CompletionProvider | Callable[[], CompletionProvider] | None = None,
        condition: Callable[[], bool] | None = None,
    ) -> Callable[[TCommandFunc], TCommandFunc]:
        """Decorator to register a function as a command.

        Args:
            name: Command name (defaults to function name)
            description: Command description (defaults to function docstring)
            category: Command category
            usage: Optional usage string
            help_text: Optional help text
            completer: Optional completion provider or factory
            condition: Optional function to check if command is available

        Example:
            ```python
            @store.command(category="tools")
            async def hello(ctx: CommandContext, name: str = "World"):
                '''Say hello to someone.'''
                await ctx.output.print(f"Hello {name}!")
            ```
        """

        def decorator(func: TCommandFunc) -> TCommandFunc:
            cmd_name = name or func.__name__.replace("_", "-")
            cmd_description = description or func.__doc__ or "No description"
            self.add_command(
                name=cmd_name,
                fn=func,
                description=cmd_description,
                category=category,
                usage=usage,
                help_text=help_text,
                completer=completer,
                condition=condition,
            )
            return func

        return decorator

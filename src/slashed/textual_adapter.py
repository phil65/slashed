"""Textual suggester adapter for Slashed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from prompt_toolkit.document import Document
from textual.app import App
from textual.containers import VerticalScroll
from textual.suggester import Suggester
from textual.widgets import Input, Label

from slashed.base import BaseCommand, OutputWriter
from slashed.completion import CompletionContext
from slashed.log import get_logger
from slashed.store import CommandStore


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from slashed.base import CommandContext
    from slashed.commands import SlashedCommand

logger = get_logger(__name__)


class TextualOutputWriter(OutputWriter):
    """Output writer that routes messages to bound widgets."""

    def __init__(self, app: App) -> None:
        self.app = app
        self._bindings: dict[str, str] = {}
        self._default_binding: str | None = None

    def bind(self, output_id: str, widget_query: str, default: bool = False) -> None:
        """Bind an output to a widget.

        Args:
            output_id: ID for this output stream
            widget_query: CSS query to find the target widget
            default: Whether this is the default output for unspecified streams
        """
        self._bindings[output_id] = widget_query
        if default:
            self._default_binding = output_id

    async def print(self, message: str, output_id: str | None = None) -> None:
        """Print message to bound widget.

        Args:
            message: Message to display
            output_id: Optional output stream ID. Uses default if not specified.
        """
        if output_id is None and self._default_binding is None:
            msg = "No default output binding configured"
            raise ValueError(msg)

        binding = self._bindings.get(
            output_id or self._default_binding,  # type: ignore
        )
        if not binding:
            msg = f"No binding found for output: {output_id}"
            raise ValueError(msg)

        widget = self.app.query_one(binding)
        if isinstance(widget, VerticalScroll):
            widget.mount(Label(message))
        elif isinstance(widget, Label):
            widget.update(message)
        else:
            # Could add more widget types here
            widget.update(message)  # type: ignore


class SlashedSuggester(Suggester):
    """Adapts a Slashed CompletionProvider to Textual's Suggester interface."""

    def __init__(
        self,
        store: CommandStore,
        context: CommandContext[Any],
        case_sensitive: bool = False,
    ) -> None:
        """Initialize suggester with store and context.

        Args:
            store: Command store for looking up commands and completers
            context: Command execution context
            case_sensitive: Whether to use case-sensitive matching
        """
        super().__init__(case_sensitive=case_sensitive)
        self._store = store
        self.context = context

    async def get_suggestion(self, value: str) -> str | None:  # noqa: PLR0911
        """Get completion suggestion for current input value."""
        if not value.startswith("/"):
            return None

        if value == "/":
            return None

        # Create document for current input
        document = Document(text=value, cursor_position=len(value))
        completion_context = CompletionContext(
            document=document, command_context=self.context
        )

        try:
            # If we have a command, use its completer
            if " " in value:  # Has arguments
                cmd_name = value.split()[0][1:]  # Remove slash
                if command := self._store.get_command(cmd_name):  # noqa: SIM102
                    if completer := command.get_completer():
                        current_word = completion_context.current_word
                        # Find first matching completion
                        for completion in completer.get_completions(completion_context):
                            if not current_word or completion.text.startswith(
                                current_word
                            ):
                                # For argument completion, preserve the cmd part
                                cmd_part = value[: value.find(" ") + 1]
                                # If we have a current word, replace it
                                if current_word:
                                    cmd_part = value[: -len(current_word)]
                                return f"{cmd_part}{completion.text}"
                        return None

                return None

            # Otherwise complete command names
            word = value[1:]  # Remove slash
            for cmd in self._store.list_commands():
                if cmd.name.startswith(word):
                    return f"/{cmd.name}"

        except Exception:  # noqa: BLE001
            return None

        return None


class SlashedApp[TContext, TResult](App[TResult]):  # type: ignore[type-var]
    """Base app with slash command support.

    This app provides slash command functionality with optional typed context data.
    Commands can access the context data through self.context.get_data().

    Type Parameters:
        TContext: Type of the command context data. When using typed context,
                 access it via self.context.get_data() to get proper type checking.
        TResult: Type of value returned by app.run(). Use None if the app
                doesn't return anything.

    Example:
        ```python
        @dataclass
        class AppState:
            count: int = 0

        class MyApp(SlashedApp[AppState, None]):
            @SlashedApp.command_input("input-id")
            async def handle_input(self, value: str) -> None:
                state = self.context.get_data()
                state.count += 1
                await self.context.output.print(f"Count: {state.count}")
        ```
    """

    # Class-level storage for command input handlers
    _command_handlers: ClassVar[dict[str, dict[str, str]]] = {}

    def __init__(
        self,
        store: CommandStore | None = None,
        data: TContext | None = None,
        commands: list[type[SlashedCommand] | BaseCommand] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize app with command store.

        Args:
            data: Optional context data
            commands: Optional list of commands to register
            store: Optional command store (creates new one if not provided)
            *args: Arguments passed to textual.App
            **kwargs: Keyword arguments passed to textual.App
        """
        super().__init__(*args, **kwargs)
        self.store = store or CommandStore()
        self.store._initialize_sync()
        writer = TextualOutputWriter(self)
        self.context = self.store.create_context(data=data, output_writer=writer)
        if commands:
            for command in commands:
                self.store.register_command(command)

    def get_suggester(self) -> SlashedSuggester:
        """Get a suggester configured for this app's store and context."""
        return SlashedSuggester(store=self.store, context=self.context)

    def bind_output(
        self, output_id: str, widget_query: str, default: bool = False
    ) -> None:
        """Bind an output stream to a widget.

        Args:
            output_id: ID for this output stream
            widget_query: CSS query to find the target widget
            default: Whether this is the default output
        """
        writer = self.context.output
        if not isinstance(writer, TextualOutputWriter):
            msg = "Output writer is not a TextualOutputWriter"
            raise TypeError(msg)
        writer.bind(output_id, widget_query, default=default)

    @classmethod
    def command_input(
        cls,
        input_id: str,
    ) -> Callable[
        [Callable[[Any, str], Awaitable[None]]], Callable[[Any, str], Awaitable[None]]
    ]:
        """Register an Input widget to handle commands.

        Args:
            input_id: ID of the Input widget that should handle commands

        Example:
            ```python
            @command_input("my-input")
            async def handle_my_input(self, value: str) -> None:
                # Handle non-command text input here
                await self.context.output.print(f"Echo: {value}")
            ```
        """

        def decorator(
            method: Callable[[Any, str], Awaitable[None]],
        ) -> Callable[[Any, str], Awaitable[None]]:
            # Store the handler method name for this class and input
            cls._command_handlers.setdefault(cls.__name__, {})[input_id] = method.__name__
            return method

        return decorator

    async def on_input_submitted(self) -> None:
        """Handle input submission."""
        input_widget = self.query_one("#command-input", Input)
        value = input_widget.value

        if value.startswith("/"):
            # Execute command
            cmd = value[1:]
            try:
                await self.store.execute_command(cmd, self.context)
            except Exception as e:  # noqa: BLE001
                self.log(f"Error: {e}")
            input_widget.value = ""
            return

        # For non-command input, call handler only if registered
        handlers = self._command_handlers.get(self.__class__.__name__, {})
        if input_widget.id in handlers:
            handler_name = handlers[input_widget.id]
            handler = getattr(self, handler_name)
            await handler(value)
            input_widget.value = ""

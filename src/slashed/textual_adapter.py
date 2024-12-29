"""Textual suggester adapter for Slashed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from prompt_toolkit.document import Document
from textual.app import App
from textual.containers import VerticalScroll
from textual.suggester import Suggester
from textual.widgets import Input, Label

from slashed.base import OutputWriter
from slashed.completion import CompletionContext
from slashed.log import get_logger
from slashed.store import CommandStore


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from slashed.base import CommandContext

logger = get_logger(__name__)


class TextualOutputWriter(OutputWriter):
    """Output writer that uses Textual widgets for output."""

    def __init__(self, app: App) -> None:
        self.app = app

    async def print(self, message: str) -> None:
        """Write message by mounting a new Label."""
        output_area = self.app.query_one("#output-area", VerticalScroll)
        output_area.mount(Label(message))


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
                        try:
                            completion = next(
                                completer.get_completions(completion_context)
                            )
                            # For argument completion, we need to preserve the cmd part
                            cmd_part = value[: value.find(" ") + 1]
                        except StopIteration:
                            return None
                        else:
                            return f"{cmd_part}{completion.text}"

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
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize app with command store."""
        super().__init__(*args, **kwargs)
        self.store = store or CommandStore()
        self.context = self.store.create_context(
            data=data, output_writer=TextualOutputWriter(self)
        )

    async def on_mount(self) -> None:
        """Initialize command store when app is mounted."""
        await self.store.initialize()

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

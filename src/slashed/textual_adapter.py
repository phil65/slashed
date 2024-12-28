"""Textual suggester adapter for Slashed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prompt_toolkit.document import Document
from textual.app import App, ComposeResult
from textual.suggester import Suggester
from textual.widgets import Input
from typing_extensions import TypeVar

from slashed.completion import CompletionContext
from slashed.output import DefaultOutputWriter
from slashed.store import CommandStore


if TYPE_CHECKING:
    from slashed.base import CommandContext, CompletionProvider

TResult = TypeVar("TResult", default=None)


class SlashedSuggester(Suggester):
    """Adapts a Slashed CompletionProvider to Textual's Suggester interface."""

    def __init__(
        self,
        provider: CompletionProvider,
        context: CommandContext[Any],
        case_sensitive: bool = False,
    ):
        """Initialize suggester with a completion provider.

        Args:
            provider: The slashed completion provider
            context: Command execution context
            case_sensitive: Whether to use case-sensitive matching
        """
        super().__init__(case_sensitive=case_sensitive)
        self.provider = provider
        self.context = context

    async def get_suggestion(self, value: str) -> str | None:
        """Get completion suggestion for current input value.

        Args:
            value: Current input value

        Returns:
            Suggested completion or None
        """
        # Create document for current input
        document = Document(text=value, cursor_position=len(value))

        # Get completion context
        ctx = CompletionContext(document=document, command_context=self.context)

        # Get first matching completion
        try:
            completion = next(self.provider.get_completions(ctx))
        except StopIteration:
            return None
        else:
            return completion.text


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
            def __init__(self) -> None:
                super().__init__(data=AppState())

            async def handle_input(self, value: str) -> None:
                state = self.context.get_data()  # typed as AppState
                state.count += 1  # type safe access
        ```
    """

    def __init__(
        self,
        store: CommandStore | None = None,
        data: TContext | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize app with command store.

        Args:
            store: Optional command store, creates new one if not provided
            data: Optional data for command context
            *args: Arguments passed to textual.App
            **kwargs: Keyword arguments passed to textual.App
        """
        super().__init__(*args, **kwargs)
        self.store = store or CommandStore()
        self.context: CommandContext[TContext] = self.store.create_context(
            data=data, output_writer=DefaultOutputWriter()
        )

    async def on_mount(self) -> None:
        """Initialize command store when app is mounted."""
        await self.store.initialize()

    def compose(self) -> ComposeResult:
        """Create command input."""
        yield Input(
            placeholder="Type a command (starts with /) or text...", id="command-input"
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.value.startswith("/"):
            # Remove leading slash and execute
            cmd = event.value[1:]
            try:
                await self.store.execute_command(cmd, self.context)
            except Exception as e:  # noqa: BLE001
                # Handle errors appropriately
                await self.context.output.print(f"Error: {e}")

            # Clear input after executing
            event.input.value = ""
            return

        # Let subclasses handle non-command input
        await self.handle_input(event.value)

    async def handle_input(self, value: str) -> None:
        """Override this to handle non-command input."""

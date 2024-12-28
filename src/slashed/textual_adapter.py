"""Textual suggester adapter for Slashed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prompt_toolkit.document import Document
from textual.app import App, ComposeResult
from textual.suggester import Suggester
from textual.widgets import Input

from slashed.completers import ChoiceCompleter
from slashed.completion import CompletionContext
from slashed.output import DefaultOutputWriter
from slashed.store import CommandStore


if TYPE_CHECKING:
    from slashed.base import CommandContext, CompletionProvider


class SlashedSuggester(Suggester):
    """Adapts a Slashed CompletionProvider to Textual's Suggester interface."""

    def __init__(
        self,
        provider: CompletionProvider,
        context: CommandContext[Any],
        case_sensitive: bool = False,
    ) -> None:
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


class SlashedApp(App[None]):
    """Base app with slash command support."""

    def __init__(
        self,
        store: CommandStore | None = None,
    ) -> None:
        """Initialize app with command store."""
        super().__init__()
        self.store = store or CommandStore()
        self.context = self.store.create_context(
            data=None, output_writer=DefaultOutputWriter()
        )

    async def on_mount(self) -> None:
        """Initialize command store when app is mounted."""
        await self.store.initialize()

        # No need to check for completer anymore
        # Just initialize the app's base functionality

    def compose(self) -> ComposeResult:
        """Create command input."""
        # Create input with a suggester for slash commands
        yield Input(
            placeholder="Type a command (starts with /) or text...",
            id="command-input",
            suggester=SlashedSuggester(
                provider=ChoiceCompleter({
                    f"/{cmd.name}": cmd.description for cmd in self.store.list_commands()
                }),
                context=self.context,
            ),
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

"""Example app showing Slashed commands integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Input

from slashed import Command, CommandContext
from slashed.completers import ChoiceCompleter
from slashed.textual_adapter import SlashedApp, SlashedSuggester


if TYPE_CHECKING:
    from textual.app import ComposeResult


@dataclass
class AppState:
    """Application state passed to commands."""

    user_name: str
    command_count: int = 0


async def greet(
    ctx: CommandContext[AppState], args: list[str], kwargs: dict[str, str]
) -> None:
    """Greet someone."""
    name = args[0] if args else "World"
    state = ctx.get_data()
    await ctx.output.print(f"Hello, {name}! (from {state.user_name})")


class DemoApp(SlashedApp[AppState, None]):
    """Demo app showing command input with completion."""

    CSS = """
    Container {
        height: auto;
        padding: 1;
    }

    #output-area {
        height: 1fr;
        border: solid green;
    }
    """

    def __init__(self, data: AppState | None = None) -> None:
        """Initialize app with custom command."""
        super().__init__(data=data)
        self.store.register_command(
            Command(
                name="greet",
                description="Greet someone",
                execute_func=greet,
                completer=ChoiceCompleter({
                    "World": "Everyone",
                    "Team": "The whole team",
                    "Phil": "The creator",
                }),
            )
        )

    def compose(self) -> ComposeResult:
        """Create app layout."""
        yield Header()
        yield Container(
            Input(
                placeholder="Type /help or /greet <name>",
                id="command-input",
                suggester=SlashedSuggester(
                    store=self.store,
                    context=self.context,
                ),
            )
        )
        yield VerticalScroll(id="output-area")

    @SlashedApp.command_input("command-input")
    async def handle_text(self, value: str) -> None:
        """Handle regular text input."""
        state = self.context.get_data()
        state.command_count += 1
        await self.context.output.print(
            f"[{state.user_name}] Echo: {value} (command #{state.command_count})"
        )


if __name__ == "__main__":
    app = DemoApp(data=AppState(user_name="Admin"))
    app.run()

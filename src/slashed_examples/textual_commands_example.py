"""Example app showing Slashed commands integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Input, Label

from slashed import ChoiceCompleter, SlashedCommand
from slashed.store import CommandStore
from slashed.textual_adapter import SlashedApp


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from slashed import CommandContext

INPUT_ID = "command-input"


@dataclass
class AppState:
    """Application state passed to commands.

    This state object will be available to all commands via ctx.get_data().
    Commands can access and modify this state to maintain persistence
    between command executions.
    """

    user_name: str
    command_count: int = 0


class GreetCommand(SlashedCommand):
    """Greet someone with a custom greeting."""

    name = "greet"
    category = "demo"

    async def execute_command(self, ctx: CommandContext[AppState], name: str = "World"):
        """Greet someone."""
        state = ctx.get_data()  # Type-safe access to AppState
        await ctx.output.print(f"Hello, {name}! (from {state.user_name})")

    def get_completer(self) -> ChoiceCompleter:
        """Provide name suggestions."""
        return ChoiceCompleter({"World": "Everyone", "Team": "The whole team"})


class DemoApp(SlashedApp[AppState, None]):
    """Demo app showing command input with completion.

    Generic parameters:
        AppState: Type of data available to commands
        None: App return type (from Textual)
    """

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

    def on_mount(self) -> None:
        """Set up output routing after widgets are mounted."""
        # Connect command output to specific widgets:
        # - Main command output goes to the scroll area
        # - Status messages go to the label
        self.bind_output("main", "#main-output", default=True)
        self.bind_output("status", "#status")

    def compose(self) -> ComposeResult:
        """Create app layout."""
        yield Header()

        # Create input with command completion
        suggester = self.get_suggester()
        msg = "Type /help or /greet <name>"
        input_widget = Input(placeholder=msg, id=INPUT_ID, suggester=suggester)
        yield Container(input_widget)

        # Output widgets - must match the IDs used in bind_output
        yield VerticalScroll(id="main-output")  # For command output
        yield Label(id="status")  # For status messages

    @SlashedApp.command_input(INPUT_ID)
    async def handle_text(self, value: str) -> None:
        """Handle non-command text input (optional).

        Remove this method if you only want to handle slash commands.
        """
        state = self.context.get_data()
        state.command_count += 1
        msg = f"[{state.user_name}] Echo: {value} (command #{state.command_count})"
        await self.context.output.print(msg)


if __name__ == "__main__":
    store = CommandStore(enable_system_commands=True)
    state = AppState(user_name="Admin")
    app = DemoApp(store=store, data=state, commands=[GreetCommand])
    app.run()

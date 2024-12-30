from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Label

from slashed import ChoiceCompleter, CommandContext, CompletionProvider, SlashedCommand
from slashed.textual_adapter import CommandTextArea


@dataclass
class AppState:
    """Application state available to commands."""

    theme: str = "light"
    command_count: int = 0


class ColorCommand(SlashedCommand):
    """Change color scheme."""

    name = "color"
    category = "settings"
    usage = "<scheme>"

    def get_completer(self) -> CompletionProvider:
        return ChoiceCompleter({
            "dark": "Dark color scheme",
            "light": "Light color scheme",
            "blue": "Blue theme",
            "green": "Green theme",
            "red": "Red theme",
        })

    async def execute_command(
        self,
        ctx: CommandContext,
        scheme: str,
    ):
        """Change the color scheme."""
        await ctx.output.print(f"Changing color scheme to: {scheme}")


class DemoApp(App[None]):
    """Demo app showing new command input with completion."""

    CSS = """
    Screen {
        layers: base dropdown;
    }

    CommandDropdown {
        layer: dropdown;
        background: $surface;
        border: solid red;
        width: auto;
        height: auto;
        min-width: 30;
    }
    """

    def compose(self) -> ComposeResult:
        """Create app layout."""
        yield Header()

        command_input = CommandTextArea[AppState](
            context_data=AppState(),
            output_id="main-output",  # ID for the commnd output
            status_id="status-area",  # ID for error messages and status
        )
        command_input.store.register_command(ColorCommand())
        yield Container(command_input)

        # Output areas - IDs must match what CommandTextArea expects
        yield VerticalScroll(id="main-output")
        yield Label(id="status")


if __name__ == "__main__":
    app = DemoApp()
    app.run()

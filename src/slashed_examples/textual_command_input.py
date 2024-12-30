from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Label

from slashed.base import CommandContext
from slashed.commands import SlashedCommand
from slashed.completers import ChoiceCompleter
from slashed.completion import CompletionProvider
from slashed.textual_adapter.command_input import CommandInput


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


class NewDemoApp(App[None]):
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

        command_input = CommandInput(
            placeholder="Type /help or /color <scheme>",
            enable_system_commands=True,
        )
        command_input.register_command(ColorCommand())
        yield Container(command_input)

        # Output areas - IDs must match what CommandInput expects
        yield VerticalScroll(id="main-output")
        yield Label(id="status")


if __name__ == "__main__":
    app = NewDemoApp()
    app.run()

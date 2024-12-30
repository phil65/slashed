from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Label

from slashed.base import CommandContext
from slashed.commands import SlashedCommand
from slashed.completers import ChoiceCompleter
from slashed.completion import CompletionProvider
from slashed.store import CommandStore
from slashed.textual_adapter.app import TextualOutputWriter
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
        layers: base dropdown;  /* Ensure we have the dropdown layer */
    }

    CommandDropdown {
        layer: dropdown;  /* Put dropdown in correct layer */
        background: $surface;
        border: solid red;
        width: auto;
        height: auto;
        min-width: 30;
    }
    """

    def __init__(self):
        super().__init__()
        self.store = CommandStore(enable_system_commands=True)
        self.output_writer = TextualOutputWriter(self)

    def compose(self) -> ComposeResult:
        """Create app layout."""
        yield Header()

        # Create containers for output
        yield Container(
            CommandInput(
                store=self.store,
                output_writer=self.output_writer,
                id="command-input",
                placeholder="Type /help or /greet <name>",
            )
        )

        # Output areas
        yield VerticalScroll(id="main-output")
        yield Label(id="status")

    async def on_mount(self) -> None:
        """Set up output routing after widgets are mounted."""
        # Create and bind output writer
        await self.store.initialize()
        self.store.register_command(ColorCommand())
        self.output_writer.bind("main", "#main-output", default=True)
        self.output_writer.bind("status", "#status")


if __name__ == "__main__":
    app = NewDemoApp()
    app.run()

"""Example app showing Slashed commands integration."""

from __future__ import annotations

from dataclasses import dataclass

from slashed.textual_adapter import SlashedApp


@dataclass
class AppState:
    """Example state maintained in command context."""

    command_count: int = 0
    last_input: str = ""


class DemoApp(
    SlashedApp[AppState, None]
):  # Pass AppState as context type, None as result type
    """Demo app showing command input with completion."""

    CSS = """
    Input {
        margin: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize app with typed state."""
        super().__init__(data=AppState())

    async def handle_input(self, value: str) -> None:
        """Handle regular input by echoing it."""
        # Here the type checker would know self.context.data is AppState
        # and provide completion/type checking for its attributes
        state = self.context.get_data()
        state.command_count += 1  # Type checker would know this exists

        await self.context.output.print(f"Echo: {value} (command #{state.command_count})")


if __name__ == "__main__":
    app = DemoApp()
    app.run()

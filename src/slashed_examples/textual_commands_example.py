"""Example app showing Slashed commands integration."""

from __future__ import annotations

from dataclasses import dataclass

from slashed.textual_adapter import SlashedApp


@dataclass
class AppState:
    """Example state maintained in command context."""

    command_count: int = 0
    last_input: str = ""


class DemoApp(SlashedApp[None]):
    """Demo app showing command input with completion."""

    CSS = """
    Input {
        margin: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize app with typed state."""
        super().__init__()  # Context data will be typed as Any

    async def handle_input(self, value: str) -> None:
        """Handle regular input by echoing it."""
        _state = self.context.data  # <- this is Any | None right now
        await self.context.output.print(f"Echo: {value}")


if __name__ == "__main__":
    app = DemoApp()
    app.run()

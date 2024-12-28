"""Example app showing Slashed commands integration."""

from __future__ import annotations

from slashed.textual_adapter import SlashedApp


class DemoApp(SlashedApp):
    """Demo app showing command input with completion."""

    CSS = """
    Input {
        margin: 1;
    }
    """

    async def handle_input(self, value: str) -> None:
        """Handle regular input by echoing it."""
        await self.context.output.print(f"Echo: {value}")


if __name__ == "__main__":
    app = DemoApp()
    app.run()

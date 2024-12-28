"""Example app showing SlashedSuggester integration."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Input

from slashed.base import CommandContext
from slashed.completers import PathCompleter
from slashed.output import DefaultOutputWriter
from slashed.store import CommandStore
from slashed.textual_adapter import SlashedSuggester


class DemoApp(App[None]):
    """Demo app showing file path completion."""

    CSS = """
    Container {
        height: auto;
        padding: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.store = CommandStore()
        self.context = CommandContext(
            output=DefaultOutputWriter(), data=None, command_store=self.store
        )

    def compose(self) -> ComposeResult:
        # Create input with path completion
        yield Header()
        yield Container(
            Input(
                suggester=SlashedSuggester(
                    provider=PathCompleter(
                        files=True, directories=True, show_hidden=False
                    ),
                    context=self.context,
                )
            )
        )


if __name__ == "__main__":
    app = DemoApp()
    app.run()

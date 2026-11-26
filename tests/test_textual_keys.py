"""Key handlers of the Textual widgets (Textual calls inspect.signature on handlers)."""

import pytest


pytest.importorskip("textual")

from textual.app import App, ComposeResult
from textual.widgets import Static

from slashed.textual_adapter.command_input import CommandInput
from slashed.textual_adapter.command_textarea import CommandTextArea


@pytest.mark.parametrize("widget_cls", [CommandInput, CommandTextArea])
async def test_typing_into_command_widgets(widget_cls: type) -> None:
    class _App(App[None]):
        def compose(self) -> ComposeResult:
            yield widget_cls(output_id="main-output")
            yield Static(id="main-output")

    app = _App()
    async with app.run_test() as pilot:
        app.query_one(widget_cls).focus()
        await pilot.press("a", "b")
        await pilot.pause()
        widget = app.query_one(widget_cls)
        assert (widget.value if widget_cls is CommandInput else widget.text) == "ab"

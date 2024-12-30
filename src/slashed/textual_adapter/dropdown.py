"""Dropdown widgets for command completion."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.widgets import OptionList
from textual.widgets.option_list import Option


if TYPE_CHECKING:
    from slashed.completion import CompletionItem


class CompletionOption(Option):
    """An option in the completion dropdown."""

    def __init__(self, completion: CompletionItem):
        display = Text.from_markup(f"[blue]{completion.text}[/]")
        if completion.metadata:
            display.append_text(Text.from_markup(f" - [green]{completion.metadata}[/]"))
        super().__init__(display)
        self.completion = completion


class CommandDropdown(OptionList):
    """Dropdown list for command completions."""

    DEFAULT_CSS = """
    CommandDropdown {
        background: $surface;
        border: solid $primary;
        height: auto;
        max-height: 10;
        min-width: 30;
        padding: 0 1;
        layer: dropdown;
    }
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "option-list--option",
        "option-list--option-highlighted",
        "option-list--option-hover-highlighted",
    }

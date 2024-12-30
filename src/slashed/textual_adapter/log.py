"""Textual-specific log handler."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from textual.widget import Widget


class UINotificationHandler(logging.Handler):
    """Log handler that shows messages as Textual notifications."""

    def __init__(self, widget: Widget) -> None:
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Only show debug/info as notifications
            if record.levelno <= logging.INFO:
                self.widget.notify(self.format(record))
        except Exception:  # noqa: BLE001
            self.handleError(record)

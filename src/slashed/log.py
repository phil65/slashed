from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from weakref import WeakSet


if TYPE_CHECKING:
    from slashed.base import OutputWriter


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name.

    Args:
        name: The name of the logger, will be prefixed with 'slashed.'

    Returns:
        A logger instance
    """
    return logging.getLogger(f"slashed.{name}")


class SessionLogHandler(logging.Handler):
    """Captures logs for display in chat session."""

    def __init__(self, output_writer: OutputWriter):
        super().__init__()
        self.output_writer = output_writer
        self.setFormatter(logging.Formatter("📝 [%(levelname)s] %(message)s"))
        self._tasks: WeakSet[asyncio.Task] = WeakSet()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            task = asyncio.create_task(self.output_writer.print(msg))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        except Exception:  # noqa: BLE001
            self.handleError(record)

    async def wait_for_tasks(self):
        """Wait for all pending log output tasks to complete."""
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

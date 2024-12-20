"""Output implementations for command system."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from slashed.base import OutputWriter


if TYPE_CHECKING:
    from rich.console import Console


class DefaultOutputWriter(OutputWriter):
    """Default output implementation using rich if available."""

    def __init__(self) -> None:
        """Initialize output writer."""
        try:
            from rich.console import Console

            self._console: Console | None = Console()
        except ImportError:
            self._console = None

    async def print(self, message: str) -> None:
        """Write message to output.

        Uses rich.Console if available, else regular print().
        """
        if self._console is not None:
            self._console.print(message)
        else:
            print(message, file=sys.stdout)

"""Output implementations for command system."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, ParamSpec

from slashed.base import OutputWriter


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from rich.console import Console

P = ParamSpec("P")


class DefaultOutputWriter(OutputWriter):
    """Default output implementation using rich if available."""

    def __init__(self, **console_kwargs: Any):
        """Initialize output writer.

        Args:
            **console_kwargs: Optional kwargs passed to rich.Console constructor
        """
        try:
            from rich.console import Console

            self._console: Console | None = Console(**console_kwargs)
        except ImportError:
            self._console = None

    async def print(self, message: str):
        """Write message to output.

        Uses rich.Console if available, else regular print().
        """
        if self._console is not None:
            self._console.print(message)
        else:
            print(message, file=sys.stdout)


class CallbackOutputWriter[P](OutputWriter):
    """Output writer that directly delegates printing to a callback function.

    The callback is fully responsible for how the message is displayed/written.
    Use this when you need complete control over the output process.
    """

    def __init__(
        self,
        callback: Callable[[str, P], Awaitable[None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._callback = callback
        self._args = args
        self._kwargs = kwargs

    async def print(self, message: str) -> None:
        await self._callback(message, *self._args, **self._kwargs)


class TransformOutputWriter[P](OutputWriter):
    """Output writer that transforms messages before printing via another writer.

    Unlike CallbackOutputWriter, this doesn't handle the actual output.
    Instead, it transforms the message and delegates printing to a base writer.
    Use this for adding prefixes, timestamps, or other message modifications.

    Default writer is DefaultOutputWriter.
    """

    def __init__(
        self,
        transform: Callable[[str, P], Awaitable[str]],
        *args: Any,
        base_writer: OutputWriter | None = None,
        **kwargs: Any,
    ) -> None:
        self._transform = transform
        self._args = args
        self._kwargs = kwargs
        self._base_writer = base_writer or DefaultOutputWriter()

    async def print(self, message: str) -> None:
        transformed = await self._transform(message, *self._args, **self._kwargs)
        await self._base_writer.print(transformed)

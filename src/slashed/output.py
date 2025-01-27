"""Output implementations for command system."""

from __future__ import annotations

import inspect
import sys
from typing import TYPE_CHECKING, Any

from slashed.base import OutputWriter


if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable

    from psygnal import SignalInstance
    from rich.console import Console


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

    async def print(self, message: str) -> None:
        """Write message to output.

        Uses rich.Console if available, else regular print().
        """
        if self._console is not None:
            self._console.print(message)
        else:
            print(message, file=sys.stdout)


class QueueOutputWriter(DefaultOutputWriter):
    """Output writer that puts messages in queue."""

    def __init__(self, queue: asyncio.Queue[str]):
        self.queue = queue

    async def print(self, message: str):
        await self.queue.put(message)


class CallbackOutputWriter(OutputWriter):
    """Output writer that directly delegates printing to a callback function.

    The callback can be either sync or async and is fully responsible for how
    the message is displayed/written.

    Examples:
        ```python
        # Async callback
        async def log_to_file(msg: str, file: str) -> None:
            with open(file, "a") as f:
                f.write(msg)

        # Sync callback
        def print_to_console(msg: str, prefix: str) -> None:
            print(f"{prefix}: {msg}")

        writer1 = CallbackOutputWriter(log_to_file, "output.log")
        writer2 = CallbackOutputWriter(print_to_console, prefix="Debug")
        ```
    """

    def __init__(
        self,
        callback: Callable[..., Any | Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize with callback and its arguments."""
        self._callback = callback
        self._args = args
        self._kwargs = kwargs

    async def print(self, message: str) -> None:
        """Write message using callback."""
        result = self._callback(message, *self._args, **self._kwargs)
        if inspect.isawaitable(result):
            await result


class TransformOutputWriter(OutputWriter):
    """Output writer that transforms messages before printing via another writer.

    Unlike CallbackOutputWriter, this doesn't handle the actual output.
    Instead, it transforms the message and delegates printing to a base writer.
    Use this for adding prefixes, timestamps, or other message modifications.

    Example:
        ```python
        async def add_timestamp(msg: str, fmt: str = "%H:%M:%S") -> str:
            from datetime import datetime
            return f"[{datetime.now().strftime(fmt)}] {msg}"

        writer = TransformOutputWriter(add_timestamp, base_writer=console_writer)
        ```
    """

    def __init__(
        self,
        transform: Callable[..., Awaitable[str]],
        *args: Any,
        base_writer: OutputWriter | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with transform function and base writer."""
        self._transform = transform
        self._args = args
        self._kwargs = kwargs
        self._base_writer = base_writer or DefaultOutputWriter()

    async def print(self, message: str) -> None:
        """Transform and write message."""
        transformed = await self._transform(message, *self._args, **self._kwargs)
        await self._base_writer.print(transformed)


class SignalingOutputWriter(OutputWriter):
    """Output writer that emits to a signal and chains to another writer."""

    def __init__(
        self, output_signal: SignalInstance, base_writer: OutputWriter | None = None
    ) -> None:
        self._output_signal = output_signal
        self._base_writer = base_writer or DefaultOutputWriter()

    async def print(self, message: str) -> None:
        self._output_signal.emit(message)
        await self._base_writer.print(message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base_writer, name)

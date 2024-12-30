"""Base class for command input widgets."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from textual.message import Message

from slashed import CommandStore
from slashed.exceptions import CommandError, ExitCommandError
from slashed.textual_adapter.app import TextualOutputWriter
from slashed.textual_adapter.dropdown import CommandDropdown
from slashed.textual_adapter.log import UINotificationHandler


if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import App
    from textual.screen import Screen


TContext = TypeVar("TContext")


class CommandWidgetMixin[TContext]:
    """Mixin that adds command functionality to input widgets."""

    id: str | None
    screen: Screen
    post_message: Callable[..., Any]
    app: App

    def __init__(
        self,
        *,  # Force keyword arguments
        context_data: TContext | None = None,
        output_id: str = "main-output",
        status_id: str | None = None,
        show_notifications: bool = False,
        enable_system_commands: bool = True,
    ) -> None:
        # Create store internally
        self.store = CommandStore(enable_system_commands=enable_system_commands)
        self.store._initialize_sync()
        self.output_writer = TextualOutputWriter(self.app)  # type: ignore
        self.context = self.store.create_context(
            data=context_data, output_writer=self.output_writer
        )
        self._showing_dropdown = False
        self._command_tasks: set[asyncio.Task[None]] = set()
        self.logger = logging.getLogger(f"slashed.textual.command_input.{self.id}")  # type: ignore
        self._output_id = output_id
        self._status_id = status_id
        if show_notifications:
            handler = UINotificationHandler(self)  # type: ignore
            handler.setLevel(logging.DEBUG)
            self.logger.addHandler(handler)

    def get_first_line(self) -> str:
        """Get content of first line."""
        raise NotImplementedError

    def clear_input(self) -> None:
        """Clear all input content."""
        raise NotImplementedError

    def get_cursor_screen_position(self) -> tuple[int, int]:
        """Get cursor position in screen coordinates."""
        raise NotImplementedError

    @property
    def is_command_mode(self) -> bool:
        """Check if current input is a command."""
        return self.get_first_line().startswith("/")

    def on_mount(self) -> None:
        """Set up when mounted."""
        self.store._initialize_sync()
        self._dropdown = CommandDropdown(id=f"{self.id}-dropdown")
        self._dropdown.can_focus = False
        self._dropdown.display = False
        self.screen.mount(self._dropdown)
        self.output_writer.bind("main", f"#{self._output_id}", default=True)
        if self._status_id:
            self.output_writer.bind("status", f"#{self._status_id}")

    def on_unmount(self) -> None:
        """Cancel all running tasks when unmounting."""
        for task in self._command_tasks:
            task.cancel()

    async def _execute_command(self, command: str) -> None:
        """Execute a command and emit result."""
        try:
            await self.store.execute_command(command, self.context)
            self.post_message(self.CommandExecuted(command))
        except ExitCommandError as e:
            # Exit command requested - post app exit message
            self.app.exit(str(e))
        except CommandError as e:
            # Regular command error - just show message
            await self.context.output.print(f"Error: {e}")
        except Exception as e:  # noqa: BLE001
            # Unexpected error
            await self.context.output.print(f"Unexpected error: {e}")

    def _create_command_task(self, command: str) -> None:
        """Create and store a command execution task."""
        task = asyncio.create_task(self._execute_command(command))

        def _done_callback(t: asyncio.Task[None]) -> None:
            self._command_tasks.discard(t)

        task.add_done_callback(_done_callback)
        self._command_tasks.add(task)

    class CommandExecuted(Message):
        """Posted when a command is executed."""

        def __init__(self, command: str):
            self.command = command
            super().__init__()

    class InputSubmitted(Message):
        """Regular text input was submitted."""

        def __init__(self, text: str):
            self.text = text
            super().__init__()

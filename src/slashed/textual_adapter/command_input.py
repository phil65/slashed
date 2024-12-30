"""Command input widget with completion for Slashed."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, ClassVar

from prompt_toolkit.document import Document
from textual import on
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Input

from slashed.completion import CompletionContext, CompletionItem
from slashed.exceptions import CommandError, ExitCommandError
from slashed.textual_adapter.dropdown import CommandDropdown, CompletionOption
from slashed.textual_adapter.log import UINotificationHandler


if TYPE_CHECKING:
    from textual.events import Key
    from textual.reactive import Reactive

    from slashed import CommandStore
    from slashed.base import CommandContext
    from slashed.textual_adapter.app import TextualOutputWriter


class CommandInput(Input):
    """Input widget for entering slash commands with completion support."""

    DEFAULT_CSS = """
    CommandInput {
        height: 3;
        border: solid $primary;
    }
    """
    value: Reactive[str]
    cursor_position: int

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("up", "navigate_up", "Previous suggestion", show=False),
        Binding("down", "navigate_down", "Next suggestion", show=False),
        Binding("escape", "hide_dropdown", "Hide suggestions", show=False),
    ]

    def __init__(
        self,
        store: CommandStore,
        data: Any | None = None,
        output_writer: TextualOutputWriter | None = None,
        placeholder: str = "Type a command...",
        show_notifications: bool = False,
        *,
        id: str | None = None,  # noqa: A002
    ):
        super().__init__(placeholder=placeholder, id=id)
        self.store = store
        self.context: CommandContext[Any] = store.create_context(
            data=data, output_writer=output_writer
        )
        self._showing_dropdown = False
        self._command_tasks: set[asyncio.Task[None]] = set()
        self.logger = logging.getLogger(f"slashed.textual.command_input.{self.id}")
        if show_notifications:
            handler = UINotificationHandler(self)
            handler.setLevel(logging.DEBUG)
            self.logger.addHandler(handler)

    def on_key(self, event: Key) -> None:
        """Handle special keys."""
        if self._showing_dropdown:
            match event.key:
                case "up":
                    self.action_navigate_up()
                    event.prevent_default()
                    event.stop()
                case "down":
                    self.action_navigate_down()
                    event.prevent_default()
                    event.stop()
                case "escape":
                    self.action_hide_dropdown()
                    event.prevent_default()
                    event.stop()
                case "enter":
                    # Accept completion
                    self.action_accept_completion()
                    # If this was an argument completion, execute the command
                    if self.value.startswith("/") and " " in self.value:
                        self._create_command_task(self.value[1:])
                        self.value = ""
                    event.prevent_default()
                    event.stop()
                case "tab":
                    # Just accept completion without executing
                    self.action_accept_completion()
                    event.prevent_default()
                    event.stop()

    def on_mount(self) -> None:
        """Mount the dropdown to the screen when input is mounted."""
        self._dropdown = CommandDropdown(id=f"{self.id}-dropdown")
        self._dropdown.can_focus = False
        self._dropdown.display = False
        self.screen.mount(self._dropdown)

    def on_unmount(self) -> None:
        """Cancel all running tasks when unmounting."""
        for task in self._command_tasks:
            task.cancel()

    def _create_command_task(self, command: str) -> None:
        """Create and store a command execution task."""
        task = asyncio.create_task(self._execute_command(command))

        def _done_callback(t: asyncio.Task[None]) -> None:
            self._command_tasks.discard(t)

        task.add_done_callback(_done_callback)
        self._command_tasks.add(task)

    def _get_completions(self) -> list[CompletionItem]:
        document = Document(text=self.value, cursor_position=self.cursor_position)
        completion_context = CompletionContext(
            document=document, command_context=self.context
        )

        parts = self.value[1:].split()

        self.logger.debug("Getting completions for parts: %s", parts)

        # Command name completion
        if not parts or (len(parts) == 1 and not self.value.endswith(" ")):
            text = completion_context.current_word.lstrip("/")
            self.logger.debug("Command completion for: %r", text)
            matches = [
                cmd for cmd in self.store.list_commands() if cmd.name.startswith(text)
            ]
            return [
                CompletionItem(text=cmd.name, metadata=cmd.description, kind="command")
                for cmd in matches
            ]

        # Argument completion
        command_name = parts[0]
        if command := self.store.get_command(command_name):
            if command_name == "help":
                # Special case for help command
                arg = parts[-1] if len(parts) > 1 else ""
                matches = [
                    cmd for cmd in self.store.list_commands() if cmd.name.startswith(arg)
                ]
                return [
                    CompletionItem(
                        text=cmd.name,
                        metadata=cmd.description,
                        kind="command-arg",  # type: ignore
                    )
                    for cmd in matches
                ]

            # For other commands, use their completer
            if completer := command.get_completer():
                self.logger.debug("Found completer for command: %s", command_name)

                # Create a new document for just the argument part
                arg_text = parts[-1] if len(parts) > 1 else ""
                arg_document = Document(text=arg_text, cursor_position=len(arg_text))
                arg_context = CompletionContext(
                    document=arg_document, command_context=self.context
                )

                completions = list(completer.get_completions(arg_context))
                num = len(completions)
                self.logger.debug("Got %s completions from command completer", num)
                return completions

        return []

    def _update_completions(self) -> None:
        """Update the completion dropdown."""
        self.logger.debug("Updating completions...")

        completions = self._get_completions()
        self._dropdown.clear_options()

        if completions:
            # Add completion options to dropdown
            options = [CompletionOption(completion) for completion in completions]
            self._dropdown.add_options(options)

            self.logger.debug("Added %s options to dropdown", len(options))

            # Show dropdown
            self._showing_dropdown = True
            self._dropdown.display = True

            # Position dropdown using cursor_screen_offset
            cursor_x, cursor_y = self.cursor_screen_offset
            self._dropdown.styles.offset = (cursor_x, cursor_y + 1)

            # Update selection
            if self._dropdown.option_count:
                self._dropdown.highlighted = 0
        else:
            self.logger.debug("No completions found, hiding dropdown")
            self.action_hide_dropdown()

    def action_hide_dropdown(self) -> None:
        """Hide the completion dropdown."""
        if self._showing_dropdown:
            self._dropdown.display = False
            self._showing_dropdown = False

    def action_navigate_up(self) -> None:
        """Move selection up in dropdown."""
        if self._showing_dropdown and self._dropdown.option_count:
            self._dropdown.action_cursor_up()

    def action_navigate_down(self) -> None:
        """Move selection down in dropdown."""
        if self._showing_dropdown and self._dropdown.option_count:
            self._dropdown.action_cursor_down()

    def action_accept_completion(self) -> None:
        """Accept the currently selected completion."""
        if not self._showing_dropdown or self._dropdown.highlighted is None:
            return

        option = self._dropdown.get_option_at_index(self._dropdown.highlighted)
        if not isinstance(option, CompletionOption):
            return

        completion = option.completion

        # Get current parts
        parts = self.value[1:].split()

        if not parts or (len(parts) == 1 and not self.value.endswith(" ")):
            # Command completion - replace whole value
            new_value = f"/{completion.text}"
        else:
            # Argument completion - replace just the last part or add new part
            if len(parts) > 1:
                parts[-1] = completion.text
            else:
                parts.append(completion.text)
            new_value = "/" + " ".join(parts)

        self.logger.debug("Accepting completion: %s", new_value)

        # Update value and move cursor to end
        self.value = new_value
        self.cursor_position = len(new_value)

        self.action_hide_dropdown()

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

    @on(Input.Submitted)
    async def _handle_submit(self, event: Input.Submitted) -> None:
        """Handle command execution on submit."""
        self.logger.debug("Submit event received: %s", self.value)

        if self.value.startswith("/"):
            command = self.value[1:]  # Remove leading slash
            await self._execute_command(command)
            self.value = ""
            event.stop()

    def on_input_changed(self, message: Input.Changed) -> None:
        """Update completions when input changes."""
        self.logger.debug("Input changed: %s", self.value)

        if self.value.startswith("/"):
            self._update_completions()
        else:
            self.action_hide_dropdown()

    class CommandExecuted(Message):
        """Posted when a command is executed."""

        def __init__(self, command: str):
            self.command = command
            super().__init__()

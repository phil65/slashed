"""Single-line command input widget with completion support."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.document import Document
from textual import on
from textual.binding import Binding
from textual.widgets import Input

from slashed.completion import CompletionContext, CompletionItem
from slashed.textual_adapter.command_base import CommandWidgetMixin
from slashed.textual_adapter.dropdown import CompletionOption


if TYPE_CHECKING:
    from textual.events import Key
    from textual.reactive import Reactive


class CommandInput[TContext](Input, CommandWidgetMixin[TContext]):
    """Single-line command input with completion support.

    Type Parameters:
        TContext: Type of the context data available to commands via ctx.get_data()
    """

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
        Binding("tab", "accept_completion", "Accept completion", show=False),
    ]

    def __init__(
        self,
        placeholder: str = "Type a command...",
        *,  # Force keyword arguments
        context_data: TContext | None = None,
        output_id: str = "main-output",
        status_id: str | None = None,
        show_notifications: bool = False,
        enable_system_commands: bool = True,
        # Widget parameters
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        # First initialize CommandWidgetBase
        Input.__init__(
            self,
            placeholder=placeholder,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        # Initialize mixin
        CommandWidgetMixin.__init__(
            self,
            context_data=context_data,
            output_id=output_id,
            status_id=status_id,
            show_notifications=show_notifications,
            enable_system_commands=enable_system_commands,
        )

    # Protocol implementation
    def get_first_line(self) -> str:
        return self.value

    def clear_input(self) -> None:
        self.value = ""

    def get_cursor_screen_position(self) -> tuple[int, int]:
        return self.cursor_screen_offset

    async def _get_completions(self) -> list[CompletionItem]:
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
                # Special case for help command - filter by current argument
                arg = parts[-1] if len(parts) > 1 else ""
                self.logger.debug("Help completion for arg: %r", arg)
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

                self.logger.debug("Getting completions for argument: %r", arg_text)
                completions = [i async for i in completer.get_completions(arg_context)]
                self.logger.debug("Got %d completions", len(completions))
                return completions

        return []

    async def _update_completions(self) -> None:
        """Update the completion dropdown."""
        self.logger.debug("Updating completions...")

        completions = await self._get_completions()
        self._dropdown.clear_options()

        if completions:
            # Add completion options to dropdown
            options = [CompletionOption(completion) for completion in completions]
            self._dropdown.add_options(options)

            self.logger.debug("Added %s options to dropdown", len(options))

            # Show dropdown
            self._showing_dropdown = True
            self._dropdown.display = True

            # Position dropdown
            x, y = self.get_cursor_screen_position()
            self._dropdown.styles.offset = (x, y + 1)

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
        self.value = new_value
        self.cursor_position = len(new_value)
        self.action_hide_dropdown()

    # Event handlers
    def on_key(self, event: Key) -> None:
        """Handle special keys."""
        # First handle dropdown-specific keys
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
                case "tab":
                    self.action_accept_completion()
                    event.prevent_default()
                    event.stop()
                case "enter":
                    # Only accept completion, don't execute yet
                    self.action_accept_completion()
                    event.prevent_default()
                    # Don't stop event - let it continue to execute command
                    return

        # Handle enter for command/text submission
        if event.key == "enter":
            if self.value.startswith("/"):
                command = self.value[1:]
                self._create_command_task(command)
                self.clear_input()
            else:
                self.post_message(self.InputSubmitted(self.value))
                self.clear_input()
            event.prevent_default()
            event.stop()

    @on(Input.Submitted)
    async def _handle_submit(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        text = self.get_first_line()
        if text.startswith("/"):
            command = text[1:]  # Remove leading slash
            await self._execute_command(command)
            self.clear_input()
            event.stop()
        else:
            self.post_message(self.InputSubmitted(text))
            self.clear_input()

    async def on_input_changed(self, message: Input.Changed) -> None:
        """Update completions when input changes."""
        self.logger.debug("Input changed: %s", self.value)

        if self.value.startswith("/"):
            await self._update_completions()
        else:
            self.action_hide_dropdown()

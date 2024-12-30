"""Multi-line command input widget with completion support."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

from prompt_toolkit.document import Document
from textual.binding import Binding
from textual.widgets import TextArea

from slashed.completion import CompletionContext, CompletionItem
from slashed.textual_adapter.command_base import CommandWidgetMixin
from slashed.textual_adapter.dropdown import CompletionOption


if TYPE_CHECKING:
    from textual.events import Key
    from textual.reactive import Reactive


class CommandTextArea[TContext](TextArea, CommandWidgetMixin[TContext]):
    """Multi-line command input with completion support.

    Type Parameters:
        TContext: Type of the context data available to commands via ctx.get_data()
    """

    DEFAULT_CSS = """
    CommandTextArea {
        height: 5;
        border: solid $primary;
    }
    """

    value: Reactive[str]

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("up", "navigate_up", "Previous suggestion", show=False),
        Binding("down", "navigate_down", "Next suggestion", show=False),
        Binding("escape", "hide_dropdown", "Hide suggestions", show=False),
        Binding("tab", "accept_completion", "Accept completion", show=False),
    ]

    def __init__(
        self,
        *,
        context_data: TContext | None = None,
        output_id: str = "main-output",
        status_id: str | None = None,
        show_notifications: bool = False,
        enable_system_commands: bool = True,
        # TextArea specific parameters
        language: str | None = None,
        theme: str = "css",
        soft_wrap: bool = True,
        tab_behavior: Literal["focus", "indent"] = "focus",
        # Widget parameters
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        # Initialize TextArea with its parameters
        TextArea.__init__(
            self,
            language=language,
            theme=theme,
            soft_wrap=soft_wrap,
            tab_behavior=tab_behavior,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        # Initialize base with shared parameters
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
        """Get the first line of input."""
        return self.document.lines[0] if self.document.lines else ""

    def clear_input(self) -> None:
        """Clear all input."""
        self.clear()

    def get_cursor_screen_position(self) -> tuple[int, int]:
        """Get cursor position in screen coordinates."""
        return self.cursor_screen_offset

    # Command completion handling
    def _get_completions(self) -> list[CompletionItem]:
        # Only show completions if cursor is on first line and it's a command
        if self.cursor_location[0] != 0 or not self.is_command_mode:
            return []

        first_line = self.get_first_line()
        document = Document(text=first_line, cursor_position=self.cursor_location[1])
        completion_context = CompletionContext(
            document=document, command_context=self.context
        )

        parts = first_line[1:].split()

        self.logger.debug("Getting completions for parts: %s", parts)

        # Command name completion
        if not parts or (len(parts) == 1 and not first_line.endswith(" ")):
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
        if (command := self.store.get_command(command_name)) and (
            completer := command.get_completer()
        ):
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

            # Position dropdown below current line
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

        # Update content using TextArea methods
        self.clear()  # Clear current content
        self.insert(new_value)  # Insert new content
        # Move cursor to end using proper row/column calculation
        self.move_cursor((0, len(new_value)))
        self.action_hide_dropdown()

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
                    return

        # Handle submission (Shift+Enter or Ctrl+Enter)
        if event.key in ["shift+enter", "ctrl+enter"]:
            if self.get_first_line().startswith("/"):
                command = self.get_first_line()[1:]
                self._create_command_task(command)
                self.clear_input()
            else:
                self.post_message(self.InputSubmitted(self.text))
                self.clear_input()
            event.prevent_default()
            event.stop()

        # Handle enter for command/text submission
        if event.key == "enter":
            if self.is_command_mode:
                command = self.get_first_line()[1:]  # Remove leading slash
                self._create_command_task(command)
            else:
                self.post_message(self.InputSubmitted(self.text))
            self.clear_input()
            event.prevent_default()
            event.stop()

    def on_text_area_changed(self, message: TextArea.Changed) -> None:
        """Handle text changes."""
        if self.is_command_mode:
            self._update_completions()
        else:
            self.action_hide_dropdown()

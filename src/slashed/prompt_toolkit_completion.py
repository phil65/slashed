"""Command completion system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from prompt_toolkit.completion import Completer, Completion

from slashed import CommandContext, CompletionContext


if TYPE_CHECKING:
    from collections.abc import Iterator

    from prompt_toolkit.document import Document

    from slashed import BaseCommand

T = TypeVar("T")


class PromptToolkitCompleter[T](Completer):
    """Adapts our completion system to prompt-toolkit."""

    def __init__(
        self,
        commands: dict[str, BaseCommand],
        command_context: CommandContext[T] | None = None,
    ) -> None:
        """Initialize completer.

        Args:
            commands: Command dictionary
            command_context: Optional context for completions
        """
        self._commands = commands
        self._command_context = command_context

    def get_completions(
        self,
        document: Document,
        complete_event: Any,
    ) -> Iterator[Completion]:
        """Get completions for the current context."""
        word_before_cursor = document.get_word_before_cursor()

        # Create completion context with command context
        completion_context = CompletionContext[T](
            document,
            command_context=self._command_context,
        )

        # Command completion
        if document.text.startswith("/"):
            text = document.text[1:]  # remove slash
            for name, cmd in self._commands.items():
                if name.startswith(text):  # Match from start of command
                    yield Completion(
                        name,
                        start_position=-len(text),  # Replace everything after slash
                        display_meta=cmd.description,
                    )
            return

        # If we have a command and it has a completer, use that
        if " " in document.text and document.text.startswith("/"):
            cmd_name = document.text.split()[0][1:]  # remove slash
            command = self._commands.get(cmd_name)
            if command and (completer := command.get_completer()):
                for item in completer.get_completions(completion_context):
                    yield item.to_prompt_toolkit(-len(word_before_cursor))

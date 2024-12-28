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
        text = document.text.lstrip()

        if not text.startswith("/"):
            return

        # Create completion context
        completion_context = CompletionContext[T](
            document=document,
            command_context=self._command_context,
        )

        # If we have a command, use its completer
        if " " in text:  # Has arguments
            cmd_name = text.split()[0][1:]  # Remove slash
            if (command := self._commands.get(cmd_name)) and (
                completer := command.get_completer()
            ):
                for item in completer.get_completions(completion_context):
                    yield item.to_prompt_toolkit(-len(completion_context.current_word))
            return

        # Otherwise complete command names
        word = text[1:]  # Remove slash
        for name, cmd in self._commands.items():
            if name.startswith(word):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display_meta=cmd.description,
                )

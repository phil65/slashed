"""Textual suggester adapter for Slashed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prompt_toolkit.document import Document
from textual.suggester import Suggester

from slashed.completion import CompletionContext
from slashed.log import get_logger


if TYPE_CHECKING:
    from slashed.base import CommandContext
    from slashed.store import CommandStore

logger = get_logger(__name__)


class SlashedSuggester(Suggester):
    """Adapts a Slashed CompletionProvider to Textual's Suggester interface."""

    def __init__(
        self,
        store: CommandStore,
        context: CommandContext[Any],
        case_sensitive: bool = False,
    ) -> None:
        """Initialize suggester with store and context.

        Args:
            store: Command store for looking up commands and completers
            context: Command execution context
            case_sensitive: Whether to use case-sensitive matching
        """
        super().__init__(case_sensitive=case_sensitive)
        self._store = store
        self.context = context

    async def get_suggestion(self, value: str) -> str | None:  # noqa: PLR0911
        """Get completion suggestion for current input value."""
        if not value.startswith("/"):
            return None

        if value == "/":
            return None

        # Create document for current input
        document = Document(text=value, cursor_position=len(value))
        completion_context = CompletionContext(
            document=document, command_context=self.context
        )

        try:
            # If we have a command, use its completer
            if " " in value:  # Has arguments
                cmd_name = value.split()[0][1:]  # Remove slash
                if command := self._store.get_command(cmd_name):  # noqa: SIM102
                    if completer := command.get_completer():
                        current_word = completion_context.current_word
                        # Find first matching completion
                        for completion in completer.get_completions(completion_context):
                            if not current_word or completion.text.startswith(
                                current_word
                            ):
                                # For argument completion, preserve the cmd part
                                cmd_part = value[: value.find(" ") + 1]
                                # If we have a current word, replace it
                                if current_word:
                                    cmd_part = value[: -len(current_word)]
                                return f"{cmd_part}{completion.text}"
                        return None

                return None

            # Otherwise complete command names
            word = value[1:]  # Remove slash
            for cmd in self._store.list_commands():
                if cmd.name.startswith(word):
                    return f"/{cmd.name}"

        except Exception:  # noqa: BLE001
            return None

        return None

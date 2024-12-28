"""Textual suggester adapter for Slashed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prompt_toolkit.document import Document
from textual.suggester import Suggester

from slashed.completion import CompletionContext


if TYPE_CHECKING:
    from slashed.base import CommandContext, CompletionProvider


class SlashedSuggester(Suggester):
    """Adapts a Slashed CompletionProvider to Textual's Suggester interface."""

    def __init__(
        self,
        provider: CompletionProvider,
        context: CommandContext[Any],
        case_sensitive: bool = False,
    ) -> None:
        """Initialize suggester with a completion provider.

        Args:
            provider: The slashed completion provider
            context: Command execution context
            case_sensitive: Whether to use case-sensitive matching
        """
        super().__init__(case_sensitive=case_sensitive)
        self.provider = provider
        self.context = context

    async def get_suggestion(self, value: str) -> str | None:
        """Get completion suggestion for current input value.

        Args:
            value: Current input value

        Returns:
            Suggested completion or None
        """
        # Create document for current input
        document = Document(text=value, cursor_position=len(value))

        # Get completion context
        ctx = CompletionContext(document=document, command_context=self.context)

        # Get first matching completion
        try:
            completion = next(self.provider.get_completions(ctx))
        except StopIteration:
            return None
        else:
            return completion.text

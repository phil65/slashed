"""Command completion system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator

    from prompt_toolkit.completion import Completion
    from prompt_toolkit.document import Document

    from slashed.base import BaseCommand
    from slashed.slashed_types import CompletionKind


@dataclass
class CompletionItem:
    """Single completion suggestion."""

    text: str
    """Text to insert"""

    display: str | None = None
    """Optional display text (defaults to text)"""

    metadata: str | None = None
    """Additional information to show"""

    kind: CompletionKind | None = None
    """Type of completion item"""

    sort_text: str | None = None
    """Optional text to use for sorting (defaults to text)"""

    def to_prompt_toolkit(self, start_position: int) -> Completion:
        """Convert to prompt_toolkit completion."""
        from prompt_toolkit.completion import Completion

        display = self.display or self.text
        return Completion(
            self.text,
            start_position=start_position,
            display=display,
            display_meta=self.metadata,
        )


class CompletionContext:
    """Context for completion operations."""

    def __init__(self, document: Document) -> None:
        """Initialize completion context from document."""
        self.document = document
        self._parse_document()

    def _parse_document(self) -> None:
        """Parse document into command and arguments."""
        text = self.document.text.lstrip()

        if not text.startswith("/"):
            self._command_name = None
            self._args = []
            self._current_word = self.document.get_word_before_cursor()
            self._arg_position = 0
            return

        parts = text[1:].split()
        self._command_name = parts[0] if parts else None
        self._args = parts[1:]
        self._current_word = self.document.get_word_before_cursor()
        self._arg_position = len(text[: self.document.cursor_position].split()) - 1

    @property
    def command_name(self) -> str | None:
        """Get current command name if any."""
        return self._command_name

    @property
    def current_word(self) -> str:
        """Get word being completed."""
        return self._current_word

    @property
    def arg_position(self) -> int:
        """Get current argument position."""
        return self._arg_position

    @property
    def command_args(self) -> list[str]:
        """Get current command arguments."""
        return self._args


class CompletionProvider(ABC):
    """Base class for completion providers."""

    @abstractmethod
    def get_completions(
        self,
        context: CompletionContext,
    ) -> Iterator[CompletionItem]:
        """Get completion suggestions.

        Args:
            context: Current completion context

        Returns:
            Iterator of completion suggestions
        """
        ...


class CommandCompleter:
    """Main command completion implementation."""

    def __init__(self, commands: dict[str, BaseCommand]) -> None:
        """Initialize command completer.

        Args:
            commands: Mapping of command names to command instances
        """
        self._commands = commands
        self._global_providers: list[CompletionProvider] = []

    def add_global_provider(self, provider: CompletionProvider) -> None:
        """Add a global completion provider."""
        self._global_providers.append(provider)

    def get_completions(
        self,
        context: CompletionContext,
    ) -> Iterator[CompletionItem]:
        """Get completions for the current context."""
        # If at start of command, complete command names
        if not context.command_name:
            word = context.current_word.lstrip("/")  # Remove slash for matching
            matching_commands = [name for name in self._commands if name.startswith(word)]

            # If exactly one match, complete it
            if len(matching_commands) == 1:
                meta = self._commands[matching_commands[0]].description
                cmd = matching_commands[0]
                yield CompletionItem(text=cmd, metadata=meta, kind="command")
            # If multiple matches, show all
            elif len(matching_commands) > 1:
                for name in matching_commands:
                    meta = self._commands[name].description
                    yield CompletionItem(text=name, metadata=meta, kind="command")
            return
        # Get command-specific completions
        command = self._commands.get(context.command_name)
        if command and (completer := command.get_completer()):
            yield from completer.get_completions(context)

        # Get global completions
        for provider in self._global_providers:
            yield from provider.get_completions(context)

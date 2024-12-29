"""Registry for collecting commands before store initialization."""
# slashed/registry.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable

    from slashed.completion import CompletionProvider
    from slashed.store import CommandStore, TCommandFunc


@dataclass(frozen=True)
class CommandEntry:
    """Command metadata collected by registry."""

    name: str
    func: Callable
    description: str | None = None
    category: str = "general"
    usage: str | None = None
    help_text: str | None = None
    completer: CompletionProvider | Callable[[], CompletionProvider] | None = None
    condition: Callable[[], bool] | None = None


class CommandRegistry:
    """Collect commands for later registration."""

    def __init__(self):
        """Initialize registry."""
        self.commands: list[CommandEntry] = []

    def command(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        category: str = "general",
        usage: str | None = None,
        help_text: str | None = None,
        completer: CompletionProvider | Callable[[], CompletionProvider] | None = None,
        condition: Callable[[], bool] | None = None,
    ) -> Callable[[TCommandFunc], TCommandFunc]:
        """Decorator to collect a command for later registration."""

        def decorator(func: TCommandFunc) -> TCommandFunc:
            cmd_name = name or func.__name__.replace("_", "-")
            entry = CommandEntry(
                name=cmd_name,
                func=func,
                description=description,
                category=category,
                usage=usage,
                help_text=help_text,
                completer=completer,
                condition=condition,
            )
            self.commands.append(entry)
            return func

        return decorator

    def register_to(self, store: CommandStore):
        """Register all collected commands to a store."""
        for entry in self.commands:
            store.add_command(
                name=entry.name,
                fn=entry.func,
                description=entry.description,
                category=entry.category,
                usage=entry.usage,
                help_text=entry.help_text,
                completer=entry.completer,
                condition=entry.condition,
            )

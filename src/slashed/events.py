"""Event definitions for command system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from slashed.base import BaseCommand, CommandContext


# Event classes
@dataclass
class CommandRegisteredEvent:
    """Event emitted when a command is registered."""

    command: BaseCommand


@dataclass
class CommandUnregisteredEvent:
    """Event emitted when a command is unregistered."""

    name: str


@dataclass
class CommandExecutedEvent[TData]:
    """Event emitted when a command is executed."""

    command: str
    context: CommandContext[TData]
    success: bool
    error: Exception | None = None

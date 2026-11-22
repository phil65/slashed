"""Tests for context registry functionality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, assert_type

import pytest

from slashed.base import BaseCommand, CommandContext
from slashed.context import ContextRegistration, ContextRegistry


if TYPE_CHECKING:
    from typing import Union  # noqa: F401


# Test data classes
@dataclass
class DatabaseContext:
    """Test database context."""

    connection: str
    timeout: int = 30


@dataclass
class UIContext:
    """Test UI context."""

    theme: str = "dark"


@dataclass
class ExtendedUIContext(UIContext):
    """Extended UI context for inheritance testing."""

    window_size: tuple[int, int] = (800, 600)


# Test commands with different union syntaxes
class OldUnionCommand(BaseCommand):
    """Command using old-style Union."""

    name = "old-union"
    description = "Test command"

    async def execute(
        self,
        ctx: CommandContext[DatabaseContext] | CommandContext[UIContext],  # type:ignore
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute with either context type."""


class NewUnionCommand(BaseCommand):
    """Command using new-style union (|)."""

    name = "new-union"
    description = "Test command"

    async def execute(
        self,
        ctx: CommandContext[DatabaseContext] | CommandContext[UIContext],
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute with either context type."""


class UnionizedContextCommand(BaseCommand):
    """Command using union of context types."""

    name = "union-ctx"
    description = "Test command"

    async def execute(
        self,
        ctx: CommandContext[DatabaseContext | UIContext],
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute with unified context type."""


# Test commands
class DatabaseCommand(BaseCommand):
    """Command requiring database context."""

    name = "db-test"
    description = "Test command"

    async def execute(
        self,
        ctx: CommandContext[DatabaseContext],
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute with database context."""


class UICommand(BaseCommand):
    """Command requiring UI context."""

    name = "ui-test"
    description = "Test command"

    async def execute(
        self,
        ctx: CommandContext[UIContext],
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute with UI context."""


class UnionCommand(BaseCommand):
    """Command accepting multiple context types."""

    name = "union-test"
    description = "Test command"

    async def execute(
        self,
        ctx: CommandContext[DatabaseContext] | CommandContext[UIContext],
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute with either context type."""


class InvalidCommand(BaseCommand):
    """Command without proper context typing."""

    name = "invalid-test"
    description = "Test command"

    async def execute(
        self,
        ctx: Any,  # type: ignore
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute without proper context typing."""


@pytest.fixture
def registry() -> ContextRegistry:
    """Fixture providing empty context registry."""
    return ContextRegistry()


@pytest.fixture
def db_context() -> DatabaseContext:
    """Fixture providing database context."""
    return DatabaseContext(connection="test://db")


@pytest.fixture
def ui_context() -> UIContext:
    """Fixture providing UI context."""
    return UIContext(theme="light")


def test_register_and_get(registry: ContextRegistry, db_context: DatabaseContext):
    """Test basic registration and retrieval."""
    # Register with metadata
    metadata = {"version": "1.0"}
    registry.register(db_context, metadata=metadata)

    # Get just the data
    retrieved = registry.get(DatabaseContext)
    assert_type(retrieved, DatabaseContext)
    assert retrieved == db_context

    # Get full registration
    registration = registry.get_registration(DatabaseContext)
    assert_type(registration, ContextRegistration[DatabaseContext])
    assert registration.data == db_context
    assert registration.metadata == metadata


def test_register_multiple(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test registering multiple contexts."""
    registry.register(db_context)
    registry.register(ui_context)

    # Both contexts should be retrievable
    assert registry.get(DatabaseContext) == db_context
    assert registry.get(UIContext) == ui_context

    # List should contain both
    contexts = list(registry.list_contexts())
    assert len(contexts) == 2  # noqa: PLR2004
    assert all(isinstance(ctx, ContextRegistration) for ctx in contexts)


def test_unregister(registry: ContextRegistry, db_context: DatabaseContext):
    """Test context unregistration."""
    registry.register(db_context)
    registry.unregister(DatabaseContext)

    with pytest.raises(KeyError, match="No context registered for type"):
        registry.get(DatabaseContext)


def test_match_command_basic(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test basic command matching."""
    registry.register(db_context)
    registry.register(ui_context)

    # Database command should match database context
    db_cmd = DatabaseCommand()
    match = registry.match_command(db_cmd)
    assert match is not None
    assert match.data == db_context

    # UI command should match UI context
    ui_cmd = UICommand()
    match = registry.match_command(ui_cmd)
    assert match is not None
    assert match.data == ui_context


def test_match_command_inheritance(registry: ContextRegistry):
    """Test command matching with context inheritance."""
    extended_ui = ExtendedUIContext()
    registry.register(extended_ui)

    # UI command should match extended UI context
    ui_cmd = UICommand()
    match = registry.match_command(ui_cmd)
    assert match is not None
    assert match.data == extended_ui


def test_match_command_union(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test command matching with union types."""
    registry.register(db_context)
    cmd = UnionCommand()

    # Should match database context
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == db_context

    # Clear and register UI context
    registry = ContextRegistry()
    registry.register(ui_context)

    # Should now match UI context
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == ui_context


def test_match_command_invalid(registry: ContextRegistry, db_context: DatabaseContext):
    """Test command matching with invalid context types."""
    registry.register(db_context)

    # Command without proper context typing
    cmd = InvalidCommand()
    match = registry.match_command(cmd)
    assert match is None


def test_get_nonexistent(registry: ContextRegistry):
    """Test getting unregistered context."""
    with pytest.raises(KeyError, match="No context registered for type"):
        registry.get(DatabaseContext)


def test_unregister_nonexistent(registry: ContextRegistry):
    """Test unregistering unregistered context."""
    with pytest.raises(KeyError, match="No context registered for type"):
        registry.unregister(DatabaseContext)


def test_old_union_matching(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test old-style Union type matching."""
    cmd = OldUnionCommand()

    # Should match database context
    registry.register(db_context)
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == db_context

    # Should match UI context
    registry = ContextRegistry()
    registry.register(ui_context)
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == ui_context


def test_new_union_matching(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test new-style union (|) type matching."""
    cmd = NewUnionCommand()

    # Should match database context
    registry.register(db_context)
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == db_context

    # Should match UI context
    registry = ContextRegistry()
    registry.register(ui_context)
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == ui_context


def test_unionized_context_matching(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test unified context type matching."""
    cmd = UnionizedContextCommand()

    # Should match database context
    registry.register(db_context)
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == db_context

    # Should match UI context
    registry = ContextRegistry()
    registry.register(ui_context)
    match = registry.match_command(cmd)
    assert match is not None
    assert match.data == ui_context


def test_multiple_contexts_priority(
    registry: ContextRegistry,
    db_context: DatabaseContext,
    ui_context: UIContext,
):
    """Test matching when multiple valid contexts are registered."""
    cmd = OldUnionCommand()

    # Register both contexts
    registry.register(db_context)
    registry.register(ui_context)

    # Should match first valid context
    match = registry.match_command(cmd)
    assert match is not None
    # Note: We're not asserting which one it matches, just that it matches one
    assert match.data in (db_context, ui_context)


def test_no_matching_context(registry: ContextRegistry):
    """Test behavior when no matching context is found."""
    cmd = OldUnionCommand()
    match = registry.match_command(cmd)
    assert match is None

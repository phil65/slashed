"""Tests for command routing system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from unittest.mock import MagicMock

import pytest

from slashed.base import CommandContext, OutputWriter
from slashed.commands import SlashedCommand
from slashed.completion import CompletionContext
from slashed.exceptions import CommandError
from slashed.router import CommandRouter
from slashed.store import CommandStore


@dataclass
class GlobalContext:
    """Test global context."""

    env: str


@dataclass
class DbContext:
    """Test database context."""

    connection: str
    timeout: int


@dataclass
class FsContext:
    """Test filesystem context."""

    base_path: str
    mode: Literal["read", "write"] = "read"


class _TestOutputWriter(OutputWriter):
    """Output writer that collects messages for testing."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def print(self, message: str) -> None:
        """Store message for later verification."""
        self.messages.append(message)


class _TestCommand(SlashedCommand):
    """Test command that works with any context."""

    name = "test"
    category = "test"

    async def execute_command(self, ctx: CommandContext[GlobalContext | DbContext]):
        """Execute test command."""
        await ctx.output.print("Test command executed")


class DbCommand(SlashedCommand):
    """Test command that requires database context."""

    name = "query"
    category = "database"

    async def execute_command(self, ctx: CommandContext[DbContext], query: str):
        """Execute database query."""
        # Remove quotes from query to match assertion
        query = query.strip("'")
        await ctx.output.print(f"Query executed: {query}")


class FsCommand(SlashedCommand):
    """Test command that requires filesystem context."""

    name = "list"
    category = "filesystem"

    async def execute_command(self, ctx: CommandContext[FsContext], path: str = "."):
        """Execute filesystem listing."""
        await ctx.output.print(f"Listing {path} in {ctx.get_data().mode} mode")


@pytest.fixture
async def router() -> CommandRouter[GlobalContext, DbContext | FsContext]:
    """Create test router with commands and contexts."""
    store = CommandStore()

    # Remove constructor to avoid pytest warning
    test_cmd = _TestCommand()
    test_cmd._help_text = None
    store.register_command(test_cmd)

    db_cmd = DbCommand()
    db_cmd._help_text = None
    store.register_command(db_cmd)

    fs_cmd = FsCommand()
    fs_cmd._help_text = None
    store.register_command(fs_cmd)

    global_ctx = GlobalContext(env="test")
    router: CommandRouter[GlobalContext, DbContext | FsContext] = CommandRouter(
        global_ctx, store
    )

    # Add routes with strict permissions
    router.add_route(
        "db",
        DbContext(connection="test:///db", timeout=30),
        "Database operations",
        allowed_commands={"query"},  # Only allow query command
    )
    router.add_route(
        "fs",
        FsContext(base_path="/test"),
        "Filesystem operations",
    )

    return router


class TestBasicRouting:
    """Test basic routing functionality."""

    def test_add_route(self, router: CommandRouter):
        """Test adding routes."""
        # Adding duplicate route should fail
        with pytest.raises(ValueError, match="Route 'db' already exists"):
            router.add_route(
                "db",
                DbContext(connection="other", timeout=10),
                "Other DB",
            )

    def test_list_routes(self, router: CommandRouter):
        """Test listing routes."""
        routes = router.list_routes()
        assert len(routes) == 2  # noqa: PLR2004
        assert routes[0].prefix == "db"
        assert routes[1].prefix == "fs"
        assert not routes[0].active
        assert not routes[1].active

        # Set active context
        router.set_active_context(router._routes["db"].context)
        routes = router.list_routes()
        assert routes[0].active
        assert not routes[1].active

    async def test_show_routes(self, router: CommandRouter):
        """Test showing routes."""
        output = _TestOutputWriter()
        await router.show_routes(output)
        assert len(output.messages) == 3  # Header + 2 routes  # noqa: PLR2004
        assert "@db:" in output.messages[1]
        assert "@fs:" in output.messages[2]


class TestRouteExecution:
    """Test command execution through routes."""

    async def test_global_execution(self, router: CommandRouter):
        """Test executing commands with global context."""
        output = _TestOutputWriter()

        # Execute global command
        await router.execute("test", output)
        assert output.messages == ["Test command executed"]

        # Global command with @ prefix should fail
        with pytest.raises(CommandError, match="Routing prefix not allowed"):
            await router.execute_global("@db test", output)

    async def test_routed_execution(self, router: CommandRouter):
        """Test executing commands through routes."""
        output = _TestOutputWriter()

        # Execute DB command through route
        await router.execute("@db query 'SELECT 1'", output)
        assert output.messages == ["Query executed: SELECT 1"]

        output.messages.clear()
        # Execute FS command through route
        await router.execute("@fs list /tmp", output)
        assert output.messages == ["Listing /tmp in read mode"]

        # Missing route prefix should fail
        with pytest.raises(CommandError, match="Missing route prefix"):
            await router.execute_routed("query 'SELECT 1'", output)

        # Unknown route should fail
        with pytest.raises(CommandError, match="Unknown route: unknown"):
            await router.execute("@unknown test", output)

        # Command not in allowed_commands should fail
        with pytest.raises(CommandError, match="Command 'test' not allowed"):
            await router.execute("@db test", output)


class TestContextSwitching:
    """Test context switching functionality."""

    async def test_active_context(self, router: CommandRouter):
        """Test setting and using active context."""
        output = _TestOutputWriter()

        # Initially uses global context
        await router.execute("test", output)
        assert output.messages == ["Test command executed"]

        output.messages.clear()
        # Set DB context as active
        db_ctx = router._routes["db"].context
        router.set_active_context(db_ctx)

        # Now uses DB context for unrouted commands
        await router.execute("query 'SELECT 1'", output)
        assert output.messages == ["Query executed: SELECT 1"]

    async def test_temporary_context(self, router: CommandRouter):
        """Test temporary context switching."""
        output = _TestOutputWriter()

        # Use DB context temporarily
        db_ctx = router._routes["db"].context
        with router.temporary_context(db_ctx):
            await router.execute("query 'SELECT 1'", output)
            assert output.messages == ["Query executed: SELECT 1"]

        output.messages.clear()
        # Should revert to global context
        await router.execute("test", output)
        assert output.messages == ["Test command executed"]


class TestCompletion:
    """Test command completion with routing."""

    @pytest.mark.asyncio  # Add this if not already present
    async def test_route_completion(self, router: CommandRouter):
        """Test completing route prefixes."""
        doc = MagicMock()
        doc.text = "@"
        doc.cursor_position = 1
        doc.get_word_before_cursor.return_value = "@"
        context: CompletionContext[Any] = CompletionContext(doc)

        store_ctx: CommandContext[Any] = router.commands.create_context(
            router.global_context,
            output_writer=_TestOutputWriter(),
        )
        context._command_context = store_ctx

        # Use list comprehension with async for
        completions = [item async for item in router.get_completions(context)]
        assert len(completions) == 2  # noqa: PLR2004
        assert any(c.text == "@db" for c in completions)
        assert any(c.text == "@fs" for c in completions)

        # Test partial prefix
        doc.text = "@d"
        doc.cursor_position = 2
        doc.get_word_before_cursor.return_value = "@d"
        context = CompletionContext[Any](doc)
        context._command_context = store_ctx

        completions = [item async for item in router.get_completions(context)]
        assert len(completions) == 1
        assert completions[0].text == "@db"

    @pytest.mark.asyncio
    async def test_command_completion(self, router: CommandRouter):
        """Test completing commands with routing."""
        doc = MagicMock()
        doc.text = "@db "
        doc.cursor_position = len("@db ")
        doc.get_word_before_cursor.return_value = ""
        context: CompletionContext[Any] = CompletionContext(doc)

        store_ctx: CommandContext[Any] = router.commands.create_context(
            router._routes["db"].context,
            output_writer=_TestOutputWriter(),
        )
        context._command_context = store_ctx

        # Use list comprehension with async for
        completions = [item async for item in router.get_completions(context)]
        assert any(c.text == "query" for c in completions)

        # Test completing global commands
        doc.text = "t"
        doc.cursor_position = 1
        doc.get_word_before_cursor.return_value = "t"
        context = CompletionContext[Any](doc)

        store_ctx = router.commands.create_context(
            router.global_context,
            output_writer=_TestOutputWriter(),
        )
        context._command_context = store_ctx

        completions = [item async for item in router.get_completions(context)]
        assert any(c.text == "test" for c in completions)


class TestErrorHandling:
    """Test error handling in router."""

    async def test_parse_errors(self, router: CommandRouter):
        """Test command parsing errors."""
        output = _TestOutputWriter()

        with pytest.raises(CommandError, match="Missing command after route"):
            await router.execute("@db", output)

        with pytest.raises(CommandError, match="Unknown route"):
            await router.execute("@unknown test", output)

    async def test_execution_errors(self, router: CommandRouter):
        """Test command execution errors."""
        output = _TestOutputWriter()

        # Try executing DB command without route or active context
        with pytest.raises(CommandError, match="Command 'query' requires a route prefix"):
            await router.execute("query 'SELECT 1'", output)

        # Try executing command that exists but isn't in allowed_commands for DB route
        with pytest.raises(CommandError, match="Command 'test' not allowed"):
            await router.execute("@db test", output)

        # Try executing unknown command
        with pytest.raises(CommandError, match="Unknown command: nonexistent"):
            await router.execute("nonexistent", output)

        # Try executing route-only command in global context (without active DB context)
        with pytest.raises(CommandError, match="Command 'query' requires a route prefix"):
            await router.execute_global("query 'SELECT 1'", output)

        # Set DB context active and try global execution - should still fail
        router.set_active_context(router._routes["db"].context)
        with pytest.raises(CommandError):
            await router.execute_global("query 'SELECT 1'", output)

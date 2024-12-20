"""Tests for command execution functionality."""

from __future__ import annotations

import pytest

from slashed.base import Command, CommandContext, parse_command
from slashed.exceptions import CommandError
from slashed.store import CommandStore


class MockOutput:
    """Mock output writer for testing."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def print(self, message: str) -> None:
        """Record message."""
        self.messages.append(message)


@pytest.fixture
def output() -> MockOutput:
    """Fixture providing mock output writer."""
    return MockOutput()


@pytest.fixture
def store() -> CommandStore:
    """Fixture providing command store."""
    return CommandStore()


@pytest.fixture
def context(store: CommandStore, output: MockOutput) -> CommandContext:
    """Fixture providing command context."""
    return store.create_context(data=None, output_writer=output)


async def test_basic_command_execution(
    store: CommandStore,
    context: CommandContext,
    output: MockOutput,
) -> None:
    """Test basic command execution."""

    # Define test command
    async def hello(
        ctx: CommandContext,
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        name = args[0] if args else "World"
        await ctx.output.print(f"Hello, {name}!")

    cmd = Command(
        name="hello",
        description="Test command",
        execute_func=hello,
    )
    store.register_command(cmd)

    # Test without args
    await store.execute_command("hello", context)
    assert output.messages == ["Hello, World!"]

    # Test with args
    output.messages.clear()
    await store.execute_command("hello Test", context)
    assert output.messages == ["Hello, Test!"]


async def test_command_with_kwargs(
    store: CommandStore,
    context: CommandContext,
    output: MockOutput,
) -> None:
    """Test command execution with keyword arguments."""

    async def greet(
        ctx: CommandContext,
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        name = kwargs.get("name", "World")
        prefix = kwargs.get("prefix", "Hello")
        await ctx.output.print(f"{prefix}, {name}!")

    cmd = Command(
        name="greet",
        description="Greeting command",
        execute_func=greet,
    )
    store.register_command(cmd)

    await store.execute_command("greet --name John --prefix Hi", context)
    assert output.messages == ["Hi, John!"]


def test_parse_command() -> None:
    """Test command string parsing."""
    # Basic command
    result = parse_command("test")
    assert result.name == "test"
    assert not result.args.args
    assert not result.args.kwargs

    # Command with args
    result = parse_command("test arg1 arg2")
    assert result.name == "test"
    assert result.args.args == ["arg1", "arg2"]
    assert not result.args.kwargs

    # Command with kwargs
    result = parse_command("test --name value")
    assert result.name == "test"
    assert not result.args.args
    assert result.args.kwargs == {"name": "value"}

    # Command with both
    result = parse_command('test arg1 --name "John Doe" arg2')
    assert result.name == "test"
    assert result.args.args == ["arg1", "arg2"]
    assert result.args.kwargs == {"name": "John Doe"}


def test_command_store_operations(store: CommandStore) -> None:
    """Test command store registration and retrieval."""
    cmd = Command(
        name="test",
        description="Test command",
        execute_func=lambda ctx, args, kwargs: None,  # type: ignore
    )

    # Test registration
    store.register_command(cmd)
    assert store.get_command("test") == cmd

    # Test duplicate registration
    with pytest.raises(ValueError, match="Command 'test' already registered"):
        store.register_command(cmd)

    # Test unregistration
    store.unregister_command("test")
    assert store.get_command("test") is None

    # Test listing
    store.register_command(cmd)
    assert cmd in store.list_commands()


def test_parse_command_errors() -> None:
    """Test command parsing error cases."""
    # Empty command
    with pytest.raises(CommandError, match="Empty command"):
        parse_command("")

    # Invalid quote
    with pytest.raises(CommandError, match="Invalid command syntax"):
        parse_command('test "unclosed')

    # Missing kwarg value
    with pytest.raises(CommandError, match="Missing value for argument"):
        parse_command("test --name")


async def test_execute_unknown_command(
    store: CommandStore,
    context: CommandContext,
) -> None:
    """Test executing non-existent command."""
    with pytest.raises(CommandError, match="Unknown command: unknown"):
        await store.execute_command("unknown", context)


async def test_context_creation(store: CommandStore, output: MockOutput) -> None:
    """Test context creation with custom output."""
    ctx = store.create_context(data=None, output_writer=output)
    assert ctx.output is output
    assert ctx.command_store is store
    assert ctx.data is None

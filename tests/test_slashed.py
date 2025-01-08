"""Tests for command execution functionality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from slashed.base import Command, CommandContext, parse_command
from slashed.exceptions import CommandError
from slashed.store import CommandStore


if TYPE_CHECKING:
    from slashed.events import CommandExecutedEvent


@dataclass
class _TestData:
    """Test data for command context."""

    value: str = "test"


@pytest.fixture
def store() -> CommandStore:
    """Fixture providing command store."""
    return CommandStore()


@pytest.fixture
def context(store: CommandStore) -> CommandContext[_TestData]:
    """Fixture providing command context."""
    return store.create_context(_TestData())


async def test_command_signals(store: CommandStore, context: CommandContext):
    """Test that command execution emits correct signals."""
    output_messages: list[str] = []
    store.output.connect(output_messages.append)

    executed_events: list[CommandExecutedEvent] = []
    store.command_executed.connect(executed_events.append)

    async def hello(ctx: CommandContext, args: list[str], kwargs: dict[str, str]):
        await ctx.output.print("Hello, World!")

    cmd = Command(name="hello", description="Test command", execute_func=hello)
    store.register_command(cmd)

    # Execute command
    await store.execute_command("hello", context)

    # Check output signal
    assert output_messages == ["Hello, World!"]

    # Check command_executed signal
    assert len(executed_events) == 1
    event = executed_events[0]
    assert event.command == "hello"
    assert event.context == context
    assert event.success

    async def test_command_error_signals(store: CommandStore, context: CommandContext):
        """Test signal emission on command error."""
        executed_events: list[CommandExecutedEvent] = []
        store.command_executed.connect(executed_events.append)

        async def failing_cmd(
            ctx: CommandContext, args: list[str], kwargs: dict[str, str]
        ):
            msg = "Command failed"
            raise ValueError(msg)

        cmd = Command(name="fail", description="Test command", execute_func=failing_cmd)
        store.register_command(cmd)

        # Execute command
        with pytest.raises(CommandError):
            await store.execute_command("fail", context)

        # Check command_executed signal
        assert len(executed_events) == 1
        event = executed_events[0]
        assert event.command == "fail"
        assert event.context == context
        assert event.success is False
        assert isinstance(event.error, ValueError)

    def test_parse_command():
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

    def test_command_store_operations(store: CommandStore):
        """Test command store registration and retrieval."""

        async def noop(ctx: CommandContext, args: list[str], kwargs: dict[str, str]): ...

        cmd = Command(name="test", description="Test command", execute_func=noop)

        # Test registration
        store.register_command(cmd)
        assert store.get_command("test") == cmd

        # Test duplicate registration
        with pytest.raises(ValueError, match="Command 'test' already registered"):
            store.register_command(cmd)

        # Test unregistration
        store.unregister_command("test")
        assert store.get_command("test") is None

    def test_parse_command_errors():
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

    async def test_execute_unknown_command(store: CommandStore, context: CommandContext):
        """Test executing non-existent command."""
        with pytest.raises(CommandError, match="Unknown command: unknown"):
            await store.execute_command("unknown", context)

    async def test_context_creation(store: CommandStore):
        """Test context creation with typed data."""
        data = _TestData(value="test-value")
        ctx = store.create_context(data)

        # Test context data typing
        assert isinstance(ctx.data, _TestData)
        assert ctx.get_data().value == "test-value"

        # Test signal connection
        output_received: list[str] = []
        store.output.connect(output_received.append)

        await ctx.output.print("test message")
        assert output_received == ["test message"]

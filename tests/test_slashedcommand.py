"""Test suite for SlashedCommand implementation."""

from __future__ import annotations

import pytest

from slashed.base import CommandContext
from slashed.commands import SlashedCommand
from slashed.exceptions import CommandError
from slashed.output import DefaultOutputWriter


class SimpleCommand(SlashedCommand):
    """A test command."""

    name = "test"
    description = "Custom description"

    async def execute_command(
        self,
        ctx: CommandContext,
        required_arg: str,
        optional_arg: str = "default",
    ) -> None:
        """Test implementation."""
        await ctx.output.print(f"{required_arg} {optional_arg}")


class FullCommand(SlashedCommand):
    """Command with all attributes set."""

    name = "full"
    category = "test"
    description = "Description"
    usage = "custom usage"
    help_text = "Custom help"

    async def execute_command(
        self,
        ctx: CommandContext,
        required_arg: str,
        optional_arg: str = "default",
    ) -> None:
        """Execute with both required and optional args."""
        await ctx.output.print(f"{required_arg} {optional_arg}")


class DocstringCommand(SlashedCommand):
    """Command using docstring as description."""

    name = "doc"

    async def execute_command(
        self,
        ctx: CommandContext,
        value: str,
    ) -> None:
        """Do something with value."""
        await ctx.output.print(value)


@pytest.fixture
def context(tmp_path):
    """Create a command context for testing."""
    writer = DefaultOutputWriter()
    return CommandContext(output=writer, data=None, command_store=None)  # type: ignore


def test_command_attributes():
    """Test that command attributes are set correctly."""
    cmd = FullCommand()
    assert cmd.name == "full"
    assert cmd.category == "test"
    assert cmd.description == "Description"
    assert cmd.usage == "custom usage"
    assert cmd.help_text == "Custom help"


def test_default_attributes():
    """Test default attribute values."""
    cmd = SimpleCommand()
    assert cmd.name == "test"
    assert cmd.category == "general"
    assert cmd.description == "Custom description"
    assert cmd.usage == "<required_arg> [--optional_arg <value>]"
    assert cmd.help_text == "Custom description"


def test_docstring_as_description():
    """Test using docstring as description."""
    cmd = DocstringCommand()
    assert cmd.description == "Command using docstring as description."


def test_missing_name():
    """Test that missing name raises TypeError."""
    with pytest.raises(TypeError, match="must define 'name' attribute"):

        class InvalidCommand(SlashedCommand):
            """Invalid command without name."""


@pytest.mark.asyncio
async def test_required_args(context):
    """Test handling of required arguments."""
    cmd = FullCommand()

    # Missing required arg
    with pytest.raises(CommandError, match="Missing required arguments: .*required_arg"):
        await cmd.execute(context, [], {})

    # With required arg
    await cmd.execute(context, ["value"], {})


@pytest.mark.asyncio
async def test_optional_args(context):
    """Test handling of optional arguments."""
    cmd = FullCommand()

    # With optional arg
    await cmd.execute(context, ["req"], {"optional_arg": "opt"})

    # Unknown arg
    with pytest.raises(CommandError, match="Unknown argument: unknown"):
        await cmd.execute(context, ["req"], {"unknown": "value"})


@pytest.mark.asyncio
async def test_argument_binding(context):
    """Test that arguments are bound correctly."""

    class BindingCommand(SlashedCommand):
        name = "bind"
        bound_args: dict | None = None

        async def execute_command(
            self,
            ctx: CommandContext,
            first: str,
            second: str = "default",
            third: str | None = None,
        ) -> None:
            self.bound_args = {
                "first": first,
                "second": second,
                "third": third,
            }

    cmd = BindingCommand()

    # Test positional args
    await cmd.execute(context, ["one"], {})
    assert cmd.bound_args == {
        "first": "one",
        "second": "default",
        "third": None,
    }

    # Test keyword args
    await cmd.execute(context, [], {"first": "1", "second": "2", "third": "3"})
    assert cmd.bound_args == {
        "first": "1",
        "second": "2",
        "third": "3",
    }


def test_usage_generation():
    """Test automatic usage string generation."""

    class UsageCommand(SlashedCommand):
        name = "usage"

        async def execute_command(
            self,
            ctx: CommandContext,
            required: str,
            optional: str = "default",
            flag: bool = False,
        ) -> None: ...

    cmd = UsageCommand()
    assert cmd.usage == "<required> [--optional <value>] [--flag <value>]"


def test_inheritance():
    """Test that inheritance works correctly."""

    class BaseCmd(SlashedCommand):
        name = "base"
        category = "test"

        async def execute_command(
            self,
            ctx: CommandContext,
            value: str,
        ) -> None:
            """Base implementation."""
            await ctx.output.print(value)

    class ChildCmd(BaseCmd):
        name = "child"

        async def execute_command(
            self,
            ctx: CommandContext,
            value: str,
            extra: str = "default",
        ) -> None:
            """Child implementation."""
            await ctx.output.print(f"{value} {extra}")

    base = BaseCmd()
    child = ChildCmd()

    assert base.name == "base"
    assert base.category == "test"
    assert child.name == "child"
    assert child.category == "test"

"""Tests for shell executor with pipes and chaining."""

from __future__ import annotations

import pytest

from slashed import (  # noqa: TC001
    CommandContext,
    CommandResult,
    CommandStore,
    ShellExecutor,
    SlashedCommand,
)


class EchoCommand(SlashedCommand):
    """Echo arguments to stdout."""

    name = "echo"
    category = "test"

    async def execute_command(
        self,
        ctx: CommandContext[None],
        *args: str,
    ) -> CommandResult:
        return CommandResult(stdout=" ".join(args) + "\n")


class CatCommand(SlashedCommand):
    """Output stdin or literal text."""

    name = "cat"
    category = "test"

    async def execute_command(
        self,
        ctx: CommandContext[None],
        text: str | None = None,
    ) -> CommandResult:
        # If text provided, output it; otherwise output stdin
        if text:
            return CommandResult(stdout=text + "\n")
        return CommandResult(stdout=ctx.stdin)


class GrepCommand(SlashedCommand):
    """Filter lines matching pattern."""

    name = "grep"
    category = "test"

    async def execute_command(
        self,
        ctx: CommandContext[None],
        pattern: str,
    ) -> CommandResult:
        lines = ctx.stdin.splitlines()
        matches = [line for line in lines if pattern in line]
        return CommandResult(stdout="\n".join(matches) + "\n" if matches else "")


class HeadCommand(SlashedCommand):
    """Output first N lines."""

    name = "head"
    category = "test"

    async def execute_command(
        self,
        ctx: CommandContext[None],
        n: int = 10,
    ) -> CommandResult:
        lines = ctx.stdin.splitlines()
        result = lines[:n]
        return CommandResult(stdout="\n".join(result) + "\n" if result else "")


class WcCommand(SlashedCommand):
    """Count lines in stdin."""

    name = "wc"
    category = "test"

    async def execute_command(
        self,
        ctx: CommandContext[None],
    ) -> CommandResult:
        lines = ctx.stdin.splitlines()
        # Filter empty lines for count
        count = len([line for line in lines if line])
        return CommandResult(stdout=f"{count}\n")


class TrueCommand(SlashedCommand):
    """Always succeed."""

    name = "true"
    category = "test"

    async def execute_command(self, ctx: CommandContext[None]) -> CommandResult:
        return CommandResult(exit_code=0)


class FalseCommand(SlashedCommand):
    """Always fail."""

    name = "false"
    category = "test"

    async def execute_command(self, ctx: CommandContext[None]) -> CommandResult:
        return CommandResult(exit_code=1)


@pytest.fixture
def store() -> CommandStore:
    """Create a store with test commands."""
    store = CommandStore()
    store.register_command(EchoCommand)
    store.register_command(CatCommand)
    store.register_command(GrepCommand)
    store.register_command(HeadCommand)
    store.register_command(WcCommand)
    store.register_command(TrueCommand)
    store.register_command(FalseCommand)
    return store


@pytest.fixture
def executor(store: CommandStore) -> ShellExecutor:
    """Create a shell executor."""
    return ShellExecutor(store)


class TestSimpleCommands:
    """Test simple command execution."""

    async def test_echo(self, store: CommandStore) -> None:
        """Test simple echo command."""
        result = await store.execute_shell_with_context("echo hello world")
        assert result.stdout == "hello world\n"
        assert result.exit_code == 0

    async def test_unknown_command(self, store: CommandStore) -> None:
        """Test unknown command returns error."""
        result = await store.execute_shell_with_context("unknown_cmd")
        assert result.exit_code == 127  # noqa: PLR2004
        assert "Unknown command" in result.stderr


class TestPipelines:
    """Test pipeline execution."""

    async def test_simple_pipe(self, store: CommandStore) -> None:
        """Test simple two-command pipe."""
        result = await store.execute_shell_with_context("echo hello | cat")
        assert result.stdout == "hello\n"
        assert result.exit_code == 0

    async def test_multi_pipe(self, store: CommandStore) -> None:
        """Test multiple pipes."""
        # echo outputs three lines, grep filters to "error" lines, wc counts
        result = await store.execute_shell_with_context(
            'cat "line1\nerror line\nline3" | grep error | wc'
        )
        assert result.stdout.strip() == "1"

    async def test_pipe_with_filtering(self, store: CommandStore) -> None:
        """Test pipe with grep filtering."""
        result = await store.execute_shell_with_context('cat "foo\nbar\nbaz\nfoobar" | grep foo')
        assert "foo" in result.stdout
        assert "bar" in result.stdout or "foobar" in result.stdout
        assert "baz" not in result.stdout

    async def test_pipe_head(self, store: CommandStore) -> None:
        """Test pipe with head limiting output."""
        result = await store.execute_shell_with_context('cat "1\n2\n3\n4\n5" | head --n 2')
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2  # noqa: PLR2004
        assert lines[0] == "1"
        assert lines[1] == "2"


class TestChaining:
    """Test command chaining with &&, ||, ;."""

    async def test_and_success(self, store: CommandStore) -> None:
        """Test && runs second command on success."""
        result = await store.execute_shell_with_context("true && echo success")
        assert result.stdout == "success\n"
        assert result.exit_code == 0

    async def test_and_failure(self, store: CommandStore) -> None:
        """Test && skips second command on failure."""
        result = await store.execute_shell_with_context("false && echo should_not_run")
        assert "should_not_run" not in result.stdout
        assert result.exit_code == 1

    async def test_or_success(self, store: CommandStore) -> None:
        """Test || skips second command on success."""
        result = await store.execute_shell_with_context("true || echo should_not_run")
        assert "should_not_run" not in result.stdout
        assert result.exit_code == 0

    async def test_or_failure(self, store: CommandStore) -> None:
        """Test || runs second command on failure."""
        result = await store.execute_shell_with_context("false || echo fallback")
        assert result.stdout == "fallback\n"
        assert result.exit_code == 0

    async def test_sequential(self, store: CommandStore) -> None:
        """Test ; runs both commands regardless."""
        result = await store.execute_shell_with_context("false ; echo runs_anyway")
        assert result.stdout == "runs_anyway\n"

    async def test_complex_chain(self, store: CommandStore) -> None:
        """Test complex chaining."""
        result = await store.execute_shell_with_context("false || echo recovered && echo continued")
        assert "recovered" in result.stdout
        assert "continued" in result.stdout


class TestCommandResult:
    """Test CommandResult behavior."""

    def test_bool_success(self) -> None:
        """Test CommandResult is truthy on success."""
        result = CommandResult(exit_code=0)
        assert result
        assert bool(result) is True

    def test_bool_failure(self) -> None:
        """Test CommandResult is falsy on failure."""
        result = CommandResult(exit_code=1)
        assert not result
        assert bool(result) is False

    def test_default_values(self) -> None:
        """Test CommandResult default values."""
        result = CommandResult()
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.exit_code == 0

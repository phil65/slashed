"""Regression tests for the 2026-11-26 review findings."""

from __future__ import annotations

import asyncio
import shlex
import sys
import time
from typing import TYPE_CHECKING, Any

import pytest

from slashed import CommandContext, CommandStore, ShellExecutor, SlashedCommand
from slashed.base import Command
from slashed.builtin.system import ExecCommand
from slashed.exceptions import CommandError


if TYPE_CHECKING:
    import pathlib

    from slashed.events import CommandExecutedEvent


async def test_help_parameter_receives_value():
    got: list[str] = []

    async def topic(ctx: CommandContext[Any], help: str = "none") -> None:  # noqa: A002
        got.append(help)

    class HelpCommand(SlashedCommand):
        """Takes a help parameter."""

        name = "helpcls"

        async def execute_command(self, ctx: CommandContext[Any], help: str = "x") -> None:  # noqa: A002
            got.append(help)

    store = CommandStore()
    store.register_command(Command(topic, name="topic"))
    store.register_command(HelpCommand)
    ctx = store.create_context(None)
    await store.execute_command("topic --help me", ctx)
    await store.execute_command("helpcls --help you", ctx)
    assert got == ["me", "you"]


async def test_help_flag_still_shows_help_for_other_commands():
    out: list[str] = []

    async def plain(ctx: CommandContext[Any]) -> None:
        msg = "must not run"
        raise AssertionError(msg)

    store = CommandStore()
    store.register_command(Command(plain, name="plain"))
    ctx = store.create_context(None, output_writer=out.append)
    await store.execute_command("plain --help 1", ctx)
    assert "Command: /plain" in out[0]


async def test_command_error_emits_failure_event():
    async def failing(ctx: CommandContext[Any]) -> None:
        msg = "nope"
        raise CommandError(msg)

    store = CommandStore()
    store.register_command(Command(failing, name="failing"))
    events: list[CommandExecutedEvent] = []
    store.command_executed.connect(events.append)
    ctx = store.create_context(None)
    for cmd in ["failing", "unknowncmd", "failing --bad 1"]:
        with pytest.raises(CommandError):
            await store.execute_command(cmd, ctx)
    assert [e.command for e in events] == ["failing", "unknowncmd", "failing --bad 1"]
    assert all(e.success is False and isinstance(e.error, CommandError) for e in events)


async def test_shell_bool_result_maps_to_exit_code():
    async def ok(ctx: CommandContext[Any]) -> bool:
        return True

    async def no(ctx: CommandContext[Any]) -> bool:
        return False

    async def echo(ctx: CommandContext[Any], *args: str) -> str:
        return " ".join(args)

    store = CommandStore()
    for fn in (ok, no, echo):
        store.register_command(Command(fn))
    executor = ShellExecutor(store)
    ctx = store.create_context(None)
    result = await executor.execute("ok && echo reached", ctx)
    assert result.exit_code == 0
    assert "reached" in result.stdout
    result = await executor.execute("no && echo reached", ctx)
    assert result.exit_code == 1
    assert "reached" not in result.stdout


PYTHON = shlex.quote(sys.executable)


async def test_exec_does_not_block_event_loop(tmp_path: pathlib.Path):
    script = tmp_path / "sleep.py"
    script.write_text("import time; time.sleep(0.5)")
    store = CommandStore()
    store.register_command(ExecCommand)
    ctx = store.create_context(None)
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    task = asyncio.create_task(ticker())
    start = time.perf_counter()
    await store.execute_command(f"exec {PYTHON} {shlex.quote(str(script))}", ctx)
    elapsed = time.perf_counter() - start
    task.cancel()
    assert ticks >= elapsed / 0.01 / 4


async def test_exec_passes_flags_through():
    out: list[str] = []
    store = CommandStore()
    store.register_command(ExecCommand)
    ctx = store.create_context(None, output_writer=out.append)
    code = "import sys; print(sys.argv[1:])"
    await store.execute_command(f"exec {PYTHON} -c '{code}' -C some/dir --count x", ctx)
    assert "['-C', 'some/dir', '--count', 'x']" in out[0]
    out.clear()
    await store.execute_command(f"exec {PYTHON} -c '{code}' --all", ctx)
    assert "['--all']" in out[0]
    out.clear()
    executor = ShellExecutor(store)
    await executor.execute(f"exec {PYTHON} -c '{code}' --help -C y", ctx)
    assert "['--help', '-C', 'y']" in out[0]


async def test_exec_failure_raises_command_error():
    store = CommandStore()
    store.register_command(ExecCommand)
    ctx = store.create_context(None)
    with pytest.raises(CommandError, match="exit code 3"):
        await store.execute_command(f"exec {PYTHON} -c 'raise SystemExit(3)'", ctx)
    with pytest.raises(CommandError, match="not found"):
        await store.execute_command("exec definitely-not-a-command-xyz", ctx)

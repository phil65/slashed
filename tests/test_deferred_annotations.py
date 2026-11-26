"""Commands whose annotations name TYPE_CHECKING-only types (PEP 649, no future import)."""

from typing import TYPE_CHECKING

from slashed.base import Command, CommandContext
from slashed.store import CommandStore


if TYPE_CHECKING:
    from slashed.events import CommandExecutedEvent  # never imported at runtime


async def test_command_with_unresolvable_annotation_runs() -> None:
    store = CommandStore()
    context = store.create_context(None)
    output: list[str] = []
    store.output.connect(output.append)

    async def show(ctx: CommandContext, count: int, event: CommandExecutedEvent | None = None):
        """Show something."""
        return count * 2

    cmd = Command(name="show", description="Show", execute_func=show)
    store.register_command(cmd)

    assert cmd.usage == "<count> [--event <value>]"
    # `count` is still coerced although another annotation cannot be resolved.
    assert await store.execute_command("show 21", context) == 42  # noqa: PLR2004
    await store.execute_command("show 1 --help x", context)
    assert any("Command: /show" in line for line in output)

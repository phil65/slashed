"""Simple hello command for testing."""

from __future__ import annotations

from slashed.base import Command, CommandContext
from slashed.exceptions import ExitCommandError


SHOW_COMMAND_HELP = """\
Display detailed help and usage information about a specific command.

Examples:
  /show-command meta
  /show-command help
"""

HELP_HELP = """\
Display help information about commands.

Usage:
  /help         - List all available commands
  /help <cmd>   - Show detailed help for a command

Example: /help register-tool
"""


async def help_command(
    ctx: CommandContext,
    args: list[str],
    kwargs: dict[str, str],
) -> None:
    """Show available commands."""
    store = ctx.command_store

    if args:  # Detail for specific command
        name = args[0]
        if cmd := store.get_command(name):
            await ctx.output.print(
                f"Command: /{cmd.name}\n"
                f"Description: {cmd.description}\n"
                f"{cmd.format_usage() or ''}"
            )
        else:
            await ctx.output.print(f"Unknown command: {name}")
        return

    # Simple flat list of commands
    await ctx.output.print("\nAvailable commands:")
    for cmd in store.list_commands():
        await ctx.output.print(f"  /{cmd.name:<16} - {cmd.description}")


async def show_command(
    ctx: CommandContext,
    args: list[str],
    kwargs: dict[str, str],
) -> None:
    """Show detailed information about a command."""
    if not args:
        await ctx.output.print("Usage: /show-command <command_name>")
        return

    command_name = args[0].strip("/")  # Remove leading slash if present
    command_store = ctx.command_store

    if command := command_store.get_command(command_name):
        sections = [
            f"Command: /{command.name}",
            f"Category: {command.category}",
            "",
            "Description:",
            command.description,
            "",
        ]
        if command.usage:
            sections.extend(["Usage:", f"/{command.name} {command.usage}", ""])
        if command.help_text:
            sections.extend(["Help:", command.help_text])

        await ctx.output.print("\n".join(sections))
    else:
        await ctx.output.print(f"Command not found: {command_name}")


async def exit_command(
    ctx: CommandContext,
    args: list[str],
    kwargs: dict[str, str],
) -> None:
    """Exit the chat session."""
    msg = "Session ended."
    raise ExitCommandError(msg)


exit_cmd = Command(
    name="exit",
    description="Exit chat session",
    execute_func=exit_command,
    category="cli",
)


show_command_cmd = Command(
    name="show-command",
    description="Show detailed information about a command",
    execute_func=show_command,
    usage="<command_name>",
    help_text=SHOW_COMMAND_HELP,
    category="help",
)


help_cmd = Command(
    name="help",
    description="Show available commands",
    execute_func=help_command,
    usage="[command]",
    help_text=HELP_HELP,
    category="system",
)

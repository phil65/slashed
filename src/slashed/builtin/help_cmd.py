"""Help command implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from slashed.base import CommandContext  # noqa: TC001
from slashed.commands import SlashedCommand
from slashed.completers import CallbackCompleter
from slashed.completion import CompletionContext, CompletionItem  # noqa: TC001
from slashed.exceptions import ExitCommandError


if TYPE_CHECKING:
    from collections.abc import Iterator

    from slashed.completion import CompletionProvider


class HelpCommand(SlashedCommand):
    """Display help information about commands.

    Usage:
      /help           List all available commands
      /help <command> Show detailed help for a command

    Example: /help exit
    """

    name = "help"
    category = "system"

    def get_completer(self) -> CompletionProvider:
        """Create completer that suggests command names."""

        def get_choices(context: CompletionContext) -> Iterator[CompletionItem]:
            store = context.command_context.command_store
            for cmd in store.list_commands():
                yield CompletionItem(
                    text=cmd.name, metadata=cmd.description, kind="command"
                )

        return CallbackCompleter(get_choices)

    async def execute_command(
        self,
        ctx: CommandContext,
        command: str | None = None,
    ):
        """Show available commands or detailed help for a specific command."""
        store = ctx.command_store
        output_lines = []

        if command:  # Detail for specific command
            if cmd := store.get_command(command):
                sections = [
                    f"## Command: /{cmd.name}",
                    f"**Category:** {cmd.category}",
                    "",
                    "**Description:**",
                    cmd.description,
                    "",
                ]
                if cmd.usage:
                    sections.extend(["**Usage:**", f"/{cmd.name} {cmd.usage}", ""])
                if cmd.help_text:
                    sections.extend(["**Help:**", cmd.help_text])

                output_lines.extend(sections)
            else:
                output_lines.append(f"**Unknown command:** {command}")
        else:
            # List all commands grouped by category
            categories = store.get_commands_by_category()
            output_lines.append("\n## Available commands:")
            for category, commands in categories.items():
                output_lines.extend([
                    f"\n{category.title()}:",
                    *[f"  /{cmd.name:<16} - *{cmd.description}*" for cmd in commands],
                ])

        await ctx.print("\n\n".join(output_lines))


class ExitCommand(SlashedCommand):
    """Exit the chat session.

    Usage:
      /exit

    Terminates the current session.
    """

    name = "exit"
    category = "system"

    async def execute_command(self, ctx: CommandContext):
        """Exit the chat session."""
        msg = "Session ended."
        raise ExitCommandError(msg)

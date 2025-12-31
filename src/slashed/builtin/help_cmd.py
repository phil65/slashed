"""Help command implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
      /help                     List all available commands
      /help <command>           Show detailed help for a command
      /help --search=<term>     Filter commands by search term
      /help --category=<cat>    Filter commands by category

    Example: /help exit
    Example: /help --search=file
    Example: /help --category=system
    """

    name = "help"
    category = "system"

    def get_completer(self) -> CompletionProvider:
        """Create completer that suggests command names."""

        def get_choices(context: CompletionContext[Any]) -> Iterator[CompletionItem]:
            store = context.command_context.command_store
            for cmd in store.list_commands():
                yield CompletionItem(text=cmd.name, metadata=cmd.description, kind="command")

        return CallbackCompleter(get_choices)

    async def execute_command(
        self,
        ctx: CommandContext[Any],
        command: str | None = None,
        *,
        search: str | None = None,
        category: str | None = None,
    ) -> None:
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

            # Apply filters
            if category:
                category_lower = category.lower()
                categories = {k: v for k, v in categories.items() if k.lower() == category_lower}

            if search:
                search_lower = search.lower()
                filtered_categories: dict[str, list[Any]] = {}
                for cat, commands in categories.items():
                    matching = [
                        cmd
                        for cmd in commands
                        if search_lower in cmd.name.lower()
                        or search_lower in cmd.description.lower()
                    ]
                    if matching:
                        filtered_categories[cat] = matching
                categories = filtered_categories

            if not categories:
                if search and category:
                    output_lines.append(
                        f"No commands found matching '{search}' in category '{category}'"
                    )
                elif search:
                    output_lines.append(f"No commands found matching '{search}'")
                elif category:
                    output_lines.append(f"No commands found in category '{category}'")
            else:
                header = "## Available commands"
                if search:
                    header += f" (matching '{search}')"
                if category:
                    header += f" (category: {category})"
                output_lines.append(f"\n{header}:")
                for cat, commands in categories.items():
                    output_lines.extend([
                        f"\n{cat.title()}:",
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

    async def execute_command(self, ctx: CommandContext[Any]) -> None:
        """Exit the chat session."""
        msg = "Session ended."
        raise ExitCommandError(msg)

"""Built-in commands for Slashed."""

from slashed.base import BaseCommand
from slashed.builtin.help_cmd import help_cmd, exit_cmd


def get_builtin_commands() -> list[BaseCommand]:
    """Get list of built-in commands."""
    return [help_cmd, exit_cmd]

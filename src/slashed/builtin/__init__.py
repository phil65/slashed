"""Built-in commands for Slashed."""

from __future__ import annotations

from slashed.builtin.help_cmd import HelpCommand, ExitCommand
from slashed.builtin.system import (
    ExecCommand,
    ProcessesCommand,
    RunCommand,
    SystemInfoCommand,
    KillCommand,
    EnvCommand,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slashed.base import BaseCommand


def get_builtin_commands() -> list[BaseCommand]:
    """Get list of built-in commands."""
    return [HelpCommand(), ExitCommand()]


def get_system_commands() -> list[BaseCommand]:
    """Get system execution commands."""
    return [
        ExecCommand(),
        RunCommand(),
        ProcessesCommand(),
        SystemInfoCommand(),
        KillCommand(),
        EnvCommand(),
    ]

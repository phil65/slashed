"""Built-in commands for Slashed."""

from slashed.base import BaseCommand
from slashed.builtin.help_cmd import help_cmd, exit_cmd
from slashed.builtin.system import (
    ExecCommand,
    ProcessesCommand,
    RunCommand,
    SystemInfoCommand,
    KillCommand,
    EnvCommand,
)


def get_builtin_commands() -> list[BaseCommand]:
    """Get list of built-in commands."""
    return [help_cmd, exit_cmd]


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

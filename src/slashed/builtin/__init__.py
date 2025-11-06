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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from slashed.base import BaseCommand


def get_builtin_commands(
    *,
    enable_help: bool = True,
    enable_exit: bool = True,
) -> list[BaseCommand]:
    """Get list of built-in commands."""
    commands: list[Any] = []
    if enable_help:
        commands.append(HelpCommand())
    if enable_exit:
        commands.append(ExitCommand())
    return commands


def get_system_commands(
    *,
    enable_exec: bool = True,
    enable_run: bool = True,
    enable_processes: bool = True,
    enable_sysinfo: bool = True,
    enable_kill: bool = True,
    enable_env: bool = True,
) -> list[BaseCommand]:
    """Get system execution commands."""
    commands: list[Any] = []
    if enable_exec:
        commands.append(ExecCommand())
    if enable_run:
        commands.append(RunCommand())
    if enable_processes:
        commands.append(ProcessesCommand())
    if enable_sysinfo:
        commands.append(SystemInfoCommand())
    if enable_kill:
        commands.append(KillCommand())
    if enable_env:
        commands.append(EnvCommand())
    return commands

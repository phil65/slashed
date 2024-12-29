"""System command implementations."""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
import os
import platform
import subprocess
import sys
from typing import TYPE_CHECKING

from slashed.commands import SlashedCommand
from slashed.completers import PathCompleter
from slashed.exceptions import CommandError


if TYPE_CHECKING:
    from slashed.base import CommandContext


class ExecCommand(SlashedCommand):
    """Execute a system command and capture its output.

    Usage:
      /exec <command> [args...]

    The command runs synchronously and returns its output.
    """

    name = "exec"
    category = "system"

    def get_completer(self) -> PathCompleter:
        """Get path completer for executables."""
        return PathCompleter(directories=True, files=True)

    async def execute_command(
        self,
        ctx: CommandContext,
        command: str,
        *args: str,
    ):
        """Execute system command synchronously."""
        try:
            result = subprocess.run(
                [command, *args],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout:
                await ctx.output.print(result.stdout.rstrip())
            if result.stderr:
                await ctx.output.print(f"stderr: {result.stderr.rstrip()}")

        except subprocess.CalledProcessError as e:
            msg = f"Command failed with exit code {e.returncode}"
            if e.stderr:
                msg = f"{msg}\n{e.stderr}"
            raise CommandError(msg) from e
        except FileNotFoundError as e:
            msg = f"Command not found: {command}"
            raise CommandError(msg) from e


class RunCommand(SlashedCommand):
    """Launch a system command asynchronously.

    Usage:
      /run <command> [args...]

    The command runs in the background without blocking.
    """

    name = "run"
    category = "system"

    def get_completer(self) -> PathCompleter:
        """Get path completer for executables."""
        return PathCompleter(directories=True, files=True)

    async def execute_command(
        self,
        ctx: CommandContext,
        command: str,
        *args: str,
    ):
        """Launch system command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await ctx.output.print(f"Started process {process.pid}")

        except FileNotFoundError as e:
            msg = f"Command not found: {command}"
            raise CommandError(msg) from e


class ProcessesCommand(SlashedCommand):
    """List running processes.

    Usage:
      /ps [--filter_by <name>]

    Shows PID, name, memory usage and status for each process.
    Optionally filter by process name.
    """

    name = "ps"
    category = "system"

    def is_available(self) -> bool:
        return find_spec("psutil") is not None

    async def execute_command(
        self,
        ctx: CommandContext,
        *,
        filter_by: str | None = None,
    ):
        """List running processes."""
        import psutil

        processes = []
        for proc in psutil.process_iter(["pid", "name", "status", "memory_percent"]):
            try:
                pinfo = proc.info
                if not filter_by or filter_by.lower() in pinfo["name"].lower():
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not processes:
            await ctx.output.print("No matching processes found")
            return

        # Sort by memory usage
        processes.sort(key=lambda x: x["memory_percent"], reverse=True)

        # Print header
        await ctx.output.print("\nPID      MEM%   STATUS    NAME")
        await ctx.output.print("-" * 50)

        # Print processes
        for proc in processes[:20]:  # Limit to top 20
            await ctx.output.print(
                f"{proc['pid']:<8} "
                f"{proc['memory_percent']:>5.1f}  "
                f"{proc['status']:<9} "
                f"{proc['name']}"
            )


class SystemInfoCommand(SlashedCommand):
    """Show system information.

    Usage:
        /sysinfo

    Displays:
        - OS information
        - CPU usage
        - Memory usage
        - Disk usage
        - Network interfaces

    Requires:
        psutil package
    """

    name = "sysinfo"
    category = "system"

    def is_available(self) -> bool:
        return find_spec("psutil") is not None

    async def execute_command(
        self,
        ctx: CommandContext,
    ):
        """Show system information."""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        info = [
            f"System: {platform.system()} {platform.release()}",
            f"Python: {sys.version.split()[0]}",
            f"CPU Usage: {cpu_percent}%",
            f"Memory: {memory.percent}% used "
            f"({memory.used // 1024 // 1024}MB of {memory.total // 1024 // 1024}MB)",
            f"Disk: {disk.percent}% used "
            f"({disk.used // 1024 // 1024 // 1024}GB of "
            f"{disk.total // 1024 // 1024 // 1024}GB)",
            f"Network interfaces: {', '.join(psutil.net_if_addrs().keys())}",
        ]
        await ctx.output.print("\n".join(info))


class KillCommand(SlashedCommand):
    """Kill a running process.

    Usage:
      /kill <pid_or_name>

    Kill process by PID or name. Numbers are treated as PIDs,
    anything else as process name.

    Examples:
      /kill 1234        # Kill by PID
      /kill notepad.exe # Kill all processes with this name
    """

    name = "kill"
    category = "system"

    def is_available(self) -> bool:
        return find_spec("psutil") is not None

    async def execute_command(
        self,
        ctx: CommandContext,
        target: str,
    ):
        """Kill a process by PID or name."""
        import psutil

        # Try to parse as PID first
        try:
            if target.isdigit():
                pid = int(target)
                process = psutil.Process(pid)
                process.terminate()
                await ctx.output.print(f"Process {pid} terminated")
                return
        except psutil.NoSuchProcess as e:
            msg = f"No process with PID {target}"
            raise CommandError(msg) from e
        except psutil.AccessDenied as e:
            msg = f"Permission denied to kill process {target}"
            raise CommandError(msg) from e

        # If not a number, treat as process name
        killed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"].lower() == target.lower():
                    proc.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            await ctx.output.print(f"Terminated {killed} process(es) named '{target}'")
        else:
            msg = f"No processes found with name '{target}'"
            raise CommandError(msg)


class EnvCommand(SlashedCommand):
    """Show or set environment variables.

    Usage:
      /env [name] [value]

    Without arguments: show all environment variables
    With name: show specific variable
    With name and value: set variable
    """

    name = "env"
    category = "system"

    async def execute_command(
        self,
        ctx: CommandContext,
        name: str | None = None,
        value: str | None = None,
    ):
        """Manage environment variables."""
        if name is None:
            # Show all variables
            for key, val in sorted(os.environ.items()):
                await ctx.output.print(f"{key}={val}")
        elif value is None:
            # Show specific variable
            if name in os.environ:
                await ctx.output.print(f"{name}={os.environ[name]}")
            else:
                await ctx.output.print(f"Variable {name} not set")
        else:
            # Set variable
            os.environ[name] = value
            await ctx.output.print(f"Set {name}={value}")

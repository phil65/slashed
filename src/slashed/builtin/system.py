"""System command implementations."""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
import os
import platform
import subprocess
import sys

from slashed.base import CommandContext  # noqa: TC001
from slashed.commands import SlashedCommand
from slashed.completers import PathCompleter
from slashed.exceptions import CommandError


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

    async def execute_command(self, ctx: CommandContext, command: str, *args: str):
        """Execute system command synchronously."""
        try:
            cmd = [command, *args]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stdout:
                await ctx.print(f"```\n{result.stdout.rstrip()}\n```")
            if result.stderr:
                await ctx.print(f"**stderr:**\n```\n{result.stderr.rstrip()}\n```")

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

    async def execute_command(self, ctx: CommandContext, command: str, *args: str):
        """Launch system command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await ctx.print(f"✅ Started process **{process.pid}**")

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

    async def execute_command(self, ctx: CommandContext, *, filter_by: str | None = None):
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
            await ctx.print("❌ No matching processes found")
            return

        # Sort by memory usage
        processes.sort(key=lambda x: x["memory_percent"], reverse=True)

        # Format as markdown table
        lines = [
            "## Running Processes",
            "",
            "| PID | MEM% | STATUS | NAME |",
            "|-----|------|--------|------|",
        ]

        # Add processes (limit to top 20)
        for proc in processes[:20]:
            lines.append(  # noqa: PERF401
                f"| {proc['pid']} | {proc['memory_percent']:.1f}% | {proc['status']} | {proc['name']} |"  # noqa: E501
            )

        await ctx.print("\n".join(lines))


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

    async def execute_command(self, ctx: CommandContext):
        """Show system information."""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        info = [
            "## System Information",
            "",
            f"**System:** {platform.system()} {platform.release()}",
            f"**Python:** {sys.version.split()[0]}",
            f"**CPU Usage:** {cpu_percent}%",
            f"**Memory:** {memory.percent}% used "
            f"({memory.used // 1024 // 1024}MB of {memory.total // 1024 // 1024}MB)",
            f"**Disk:** {disk.percent}% used "
            f"({disk.used // 1024 // 1024 // 1024}GB of "
            f"{disk.total // 1024 // 1024 // 1024}GB)",
            f"**Network interfaces:** `{', '.join(psutil.net_if_addrs().keys())}`",
        ]
        await ctx.print("\n".join(info))


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

    async def execute_command(self, ctx: CommandContext, target: str):
        """Kill a process by PID or name."""
        import psutil

        # Try to parse as PID first
        try:
            if target.isdigit():
                pid = int(target)
                process = psutil.Process(pid)
                process.terminate()
                await ctx.print(f"✅ Process **{pid}** terminated")
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
            await ctx.print(f"✅ Terminated **{killed}** process(es) named `{target}`")
        else:
            msg = f"No processes found with name {target!r}"
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
            # Show all variables as markdown table
            lines = [
                "## Environment Variables",
                "",
                "| Variable | Value |",
                "|----------|-------|",
            ]
            for key, val in sorted(os.environ.items()):
                # Truncate long values for readability
                display_val = val if len(val) <= 50 else f"{val[:47]}..."  # noqa: PLR2004
                lines.append(f"| `{key}` | `{display_val}` |")
            await ctx.print("\n".join(lines))
        elif value is None:
            # Show specific variable
            if name in os.environ:
                await ctx.print(f"**{name}:** `{os.environ[name]}`")
            else:
                await ctx.print(f"❌ Variable `{name}` not set")
        else:
            # Set variable
            os.environ[name] = value
            await ctx.print(f"✅ Set **{name}** = `{value}`")

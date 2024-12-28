"""Declarative command system."""

from __future__ import annotations

from abc import abstractmethod
import inspect
from typing import Any

from slashed.base import BaseCommand, CommandContext
from slashed.exceptions import CommandError


class SlashedCommand(BaseCommand):
    """Base class for declarative commands.

    Allows defining commands using class syntax with explicit parameters:

    Example:
        class AddWorkerCommand(SlashedCommand):
            '''Add a new worker to the pool.'''

            name = "add-worker"
            category = "tools"

            async def execute_command(
                self,
                ctx: CommandContext,
                worker_id: str,     # required param (no default)
                host: str,          # required param (no default)
                port: int = 8080,   # optional param (has default)
            ) -> None:
                await ctx.output.print(f"Adding worker {worker_id} at {host}:{port}")
    """

    name: str
    """Command name"""

    category: str = "general"
    """Command category"""

    description: str = ""
    """Optional description override"""

    usage: str | None = None
    """Optional usage override"""

    help_text: str = ""
    """Optional help text override"""

    def __init__(self) -> None:
        """Initialize command instance."""
        self.description = (
            self.description or inspect.getdoc(self.__class__) or "No description"
        )
        self.help_text = type(self).help_text or self.description

    def __init_subclass__(cls) -> None:
        """Process command class at definition time.

        Validates required attributes and generates description/usage from metadata.
        """
        super().__init_subclass__()

        if not hasattr(cls, "name"):
            msg = f"Command class {cls.__name__} must define 'name' attribute"
            raise TypeError(msg)

        # Get description from docstring if empty
        if not cls.description:
            cls.description = inspect.getdoc(cls) or "No description"

        # Generate usage from execute signature if not set
        if cls.usage is None:
            sig = inspect.signature(cls.execute_command)
            params = []
            # Skip self and ctx parameters
            for name, param in list(sig.parameters.items())[2:]:
                if param.default == inspect.Parameter.empty:
                    params.append(f"<{name}>")
                else:
                    params.append(f"[--{name} <value>]")
            cls.usage = " ".join(params)

    @abstractmethod
    async def execute_command(
        self,
        ctx: CommandContext,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Execute the command logic.

        This method should be implemented with explicit parameters.
        Parameters without default values are treated as required.

        Args:
            ctx: Command execution context
            *args: Method should define explicit positional parameters
            **kwargs: Method should define explicit keyword parameters
        """

    async def execute(
        self,
        ctx: CommandContext,
        args: list[str],
        kwargs: dict[str, str],
    ) -> None:
        """Execute command by binding command-line arguments to method parameters."""
        # Get concrete method's signature
        method = type(self).execute_command
        sig = inspect.signature(method)

        # Get parameter information (skip self, ctx)
        parameters = dict(list(sig.parameters.items())[2:])

        # Get required parameters in order
        required = [
            name
            for name, param in parameters.items()
            if param.default == inspect.Parameter.empty
        ]

        # Check if required args are provided either as positional or keyword
        missing = [
            name
            for name in required
            if name not in kwargs and len(args) < required.index(name) + 1
        ]
        if missing:
            msg = f"Missing required arguments: {missing}"
            raise CommandError(msg)

        # Validate keyword arguments
        for name in kwargs:
            if name not in parameters:
                msg = f"Unknown argument: {name}"
                raise CommandError(msg)

        # Call with positional args first, then kwargs
        await self.execute_command(ctx, *args, **kwargs)

"""Declarative command system."""

from __future__ import annotations

from abc import abstractmethod
import inspect
from typing import TYPE_CHECKING, Any

from slashed.base import BaseCommand, extract_usage_params, parse_args


if TYPE_CHECKING:
    from slashed.base import CommandContext


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
                ctx: CommandContext,  # Optional depending on implementation
                worker_id: str,       # required param (no default)
                host: str,            # required param (no default)
                port: int = 8080,     # optional param (has default)
            ):
                await ctx.print(f"Adding worker {worker_id} at {host}:{port}")

        # Context-free command
        class VersionCommand(SlashedCommand):
            '''Show version information.'''

            name = "version"

            async def execute_command(self, major: int, minor: int = 0):
                return f"v{major}.{minor}"
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
        self.description = self.description or inspect.getdoc(self.__class__) or "No description"
        self.help_text = type(self).help_text or self.description

    def __init_subclass__(cls) -> None:
        """Process command class at definition time.

        Validates required attributes and generates description/usage from metadata.
        """
        super().__init_subclass__()

        if not hasattr(cls, "name"):
            msg = f"Command class {cls.__name__} must define 'name' attribute"
            raise TypeError(msg)

        # Get description from docstring if not explicitly set on this class
        if "description" not in cls.__dict__:
            # Check if this class has its own docstring (not inherited)
            own_doc = cls.__dict__.get("__doc__")
            if own_doc:
                cls.description = own_doc
            # Otherwise inherit parent's description (already set from parent's __init_subclass__)
            # If no parent description exists, use "No description"
            elif not hasattr(cls, "description") or not cls.description:
                cls.description = "No description"

        # Generate usage from execute signature if not explicitly set on THIS class
        if "usage" not in cls.__dict__:
            usage_params = extract_usage_params(cls.execute_command, skip_first=True)
            cls.usage = " ".join(usage_params)

    @abstractmethod
    async def execute_command(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the command logic.

        This method should be implemented with explicit parameters.
        Parameters without default values are treated as required.

        Args:
            args: Command arguments (may include context as first param)
            kwargs: Command keyword arguments
        """

    async def execute(
        self,
        ctx: CommandContext[Any],
        args: list[str],
        kwargs: dict[str, str],
    ) -> Any:
        """Execute command by binding command-line arguments to method parameters."""
        method = type(self).execute_command
        call_args = parse_args(method, ctx, args, kwargs, skip_first=True)
        return await self.execute_command(*call_args, **kwargs)

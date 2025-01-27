"""Command routing system."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from slashed.completion import CompletionContext, CompletionItem
from slashed.exceptions import CommandError
from slashed.log import get_logger


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from slashed.base import OutputWriter
    from slashed.store import CommandStore

logger = get_logger(__name__)

TGlobalContext = TypeVar("TGlobalContext")
TRouteContext = TypeVar("TRouteContext")


@dataclass
class Route[TContext]:
    """Route configuration."""

    prefix: str
    """Route prefix without @ symbol"""

    context: TContext
    """Context for this route"""

    description: str
    """Route description"""

    allowed_commands: set[str] | None = None
    """Optional set of allowed commands for this route"""

    def can_execute(self, command: str) -> bool:
        """Check if command is allowed for this route.

        Args:
            command: Command name to check

        Returns:
            True if command is allowed, False otherwise
        """
        return not self.allowed_commands or command in self.allowed_commands


@dataclass
class RouteInfo:
    """Information about a route for display."""

    prefix: str
    description: str
    active: bool


@dataclass
class ParsedRoute[TContext]:
    """Parsed routing information."""

    context: TContext
    command: str
    route: Route[TContext] | None = None


class CommandRouter[TGlobalContext, TRouteContext]:
    """Generic command router supporting context-based routing.

    Type Parameters:
        TGlobalContext: Type of the global context
        TRouteContext: Type of route-specific contexts

    Example:
        ```python
        router = CommandRouter(global_context, command_store)
        router.add_route("db", db_context, "Database commands")
        router.add_route("fs", fs_context, "Filesystem operations")

        # Execute with routing
        await router.execute("@db list-tables", output)
        await router.execute("@fs list-files", output)

        # Execute with default context
        await router.execute("help", output)
        ```
    """

    def __init__(
        self,
        global_context: TGlobalContext,
        commands: CommandStore,
    ):
        """Initialize router.

        Args:
            global_context: Default context for unrouted commands
            commands: Command store for execution
        """
        self.global_context = global_context
        self.commands = commands
        self._active_context: TRouteContext | None = None
        self._routes: dict[str, Route[TRouteContext]] = {}
        self._context_stack: list[TRouteContext | None] = []

    def add_route(
        self,
        prefix: str,
        context: TRouteContext,
        description: str = "",
        allowed_commands: set[str] | None = None,
    ) -> None:
        """Add a routable context.

        Args:
            prefix: Route prefix (without @)
            context: Context for this route
            description: Route description
            allowed_commands: Optional set of allowed command names

        Raises:
            ValueError: If route prefix already exists
        """
        if prefix in self._routes:
            msg = f"Route '{prefix}' already exists"
            raise ValueError(msg)

        route = Route(
            prefix=prefix,
            context=context,
            description=description,
            allowed_commands=allowed_commands,
        )
        self._routes[prefix] = route
        logger.debug("Added route: %s (%s)", prefix, description)

    def set_active_context(self, context: TRouteContext | None) -> None:
        """Set default context for unrouted commands.

        Args:
            context: Context to set as active, or None to use global
        """
        self._active_context = context

    @contextmanager
    def temporary_context(self, context: TRouteContext) -> Iterator[None]:
        """Temporarily switch context.

        Args:
            context: Context to use temporarily

        Example:
            ```python
            with router.temporary_context(db_context):
                await router.execute("list-tables", output)
            ```
        """
        self._context_stack.append(self._active_context)
        self._active_context = context
        try:
            yield
        finally:
            self._active_context = self._context_stack.pop()

    def list_routes(self) -> list[RouteInfo]:
        """List available routes with descriptions.

        Returns:
            List of route information
        """
        return [
            RouteInfo(
                prefix=route.prefix,
                description=route.description,
                active=route.context == self._active_context,
            )
            for route in self._routes.values()
        ]

    async def show_routes(self, output: OutputWriter) -> None:
        """Display available routes.

        Args:
            output: Output writer to use
        """
        await output.print("\nAvailable routes:")
        for route in self._routes.values():
            active = " (active)" if route.context == self._active_context else ""
            await output.print(f"@{route.prefix}: {route.description}{active}")

    def _parse_route_internal(
        self, command: str
    ) -> ParsedRoute[TGlobalContext | TRouteContext]:
        """Internal method for initial route parsing."""
        if not command.startswith("@"):
            # No route - check if command is restricted to a route
            command_name = command.split()[0]

            # If we have an active context, check if it matches any route context
            if self._active_context:
                for route in self._routes.values():
                    if route.context == self._active_context:
                        # We're in the right context,
                        # allow the command if it's in allowed_commands
                        if (
                            not route.allowed_commands
                            or command_name in route.allowed_commands
                        ):
                            return ParsedRoute[TGlobalContext | TRouteContext](
                                context=self._active_context,
                                command=command,
                            )
                        break  # Found matching route but command not allowed

            # No matching active context, check if command is restricted
            for route in self._routes.values():
                if route.allowed_commands and command_name in route.allowed_commands:
                    # Command is restricted to a route but no route specified
                    msg = f"Command '{command_name}' requires a route prefix"
                    raise CommandError(msg)

            return ParsedRoute[TGlobalContext | TRouteContext](
                context=self._active_context or self.global_context,
                command=command,
            )

        prefix, _, rest = command.partition(" ")
        route_name = prefix.lstrip("@")

        if not rest:
            msg = "Missing command after route prefix"
            raise CommandError(msg)

        if route_name not in self._routes:
            msg = f"Unknown route: {route_name}"
            raise CommandError(msg)

        route = self._routes[route_name]
        command_name = rest.split()[0]

        if not route.can_execute(command_name):
            msg = f"Command '{command_name}' not allowed for route @{route_name}"
            raise CommandError(msg)

        unified_route: Route[TGlobalContext | TRouteContext] = route  # type: ignore
        return ParsedRoute[TGlobalContext | TRouteContext](
            context=route.context,
            command=rest,
            route=unified_route,
        )

    def parse_global_command(self, command: str) -> ParsedRoute[TGlobalContext]:
        """Parse a command using global context.

        Args:
            command: Command string without routing prefix

        Returns:
            Parsed route with global context

        Raises:
            CommandError: If command uses routing prefix
        """
        if command.startswith("@"):
            msg = "Routing prefix not allowed for global commands"
            raise CommandError(msg)

        # Check if command is restricted to a route
        command_name = command.split()[0]
        for route in self._routes.values():
            if route.allowed_commands and command_name in route.allowed_commands:
                # Command is restricted to a route but no route specified
                msg = f"Command '{command_name}' requires a route prefix"
                raise CommandError(msg)

        return ParsedRoute(context=self.global_context, command=command)

    def parse_routed_command(self, command: str) -> ParsedRoute[TRouteContext]:
        """Parse a command with routing prefix.

        Args:
            command: Command string with @prefix

        Returns:
            Parsed route with route-specific context

        Raises:
            CommandError: If command doesn't use routing or route is invalid
        """
        if not command.startswith("@"):
            msg = "Missing route prefix"
            raise CommandError(msg)

        parsed = self._parse_route_internal(command)
        if isinstance(parsed.context, type(self.global_context)):
            msg = "Unexpected global context for routed command"
            raise RuntimeError(msg)  # noqa: TRY004

        # We know it's TRouteContext at this point
        context = parsed.context
        if not isinstance(context, type(self._routes[next(iter(self._routes))].context)):
            msg = "Invalid context type for routed command"
            raise RuntimeError(msg)  # noqa: TRY004

        return ParsedRoute[TRouteContext](
            context=context,  # type: ignore  # We've verified the type
            command=parsed.command,
            route=parsed.route,  # type: ignore  # We know it's the right type
        )

    async def execute(
        self,
        command: str,
        output: OutputWriter,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Execute command with appropriate context."""
        parsed = self._parse_route_internal(command)
        ctx = self.commands.create_context(
            parsed.context,
            output_writer=output,
            metadata=metadata,
        )
        await self.commands.execute_command(parsed.command, ctx)

    async def execute_global(
        self,
        command: str,
        output: OutputWriter,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Execute command with global context."""
        parsed = self.parse_global_command(command)
        ctx = self.commands.create_context(
            parsed.context,
            output_writer=output,
            metadata=metadata,
        )
        await self.commands.execute_command(parsed.command, ctx)

    async def execute_routed(
        self,
        command: str,
        output: OutputWriter,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Execute command with route-specific context."""
        parsed = self.parse_routed_command(command)
        ctx = self.commands.create_context(
            parsed.context,
            output_writer=output,
            metadata=metadata,
        )
        await self.commands.execute_command(parsed.command, ctx)

    async def get_completions(
        self,
        context: CompletionContext,
    ) -> AsyncIterator[CompletionItem]:
        """Get completions including route prefixes."""
        word = context.current_word
        text = context._document.text

        # Complete route prefixes
        if word.startswith("@"):
            prefix = word[1:]
            for route in self._routes.values():
                if route.prefix.startswith(prefix):
                    yield CompletionItem(
                        text=f"@{route.prefix}",
                        metadata=route.description,
                        kind="route",  # type: ignore
                    )
            return

        # Get route-specific completions
        try:
            # If we're after a route prefix, use that context
            parts = text.split()
            if parts and parts[0].startswith("@"):
                route_name = parts[0][1:]
                if route_name in self._routes:
                    route = self._routes[route_name]
                    # Create completion context with route context
                    route_ctx = self.commands.create_context(
                        route.context,
                        output_writer=context.command_context.output,
                    )
                    route_completion_ctx = CompletionContext(
                        document=context._document,
                        command_context=route_ctx,
                    )
                    # Use the command completer
                    if command := self.commands._commands.get(word):
                        if completer := command.get_completer():
                            async for item in completer.get_completions(
                                route_completion_ctx
                            ):
                                yield item
                    # Or suggest commands
                    else:
                        commands = self.commands.list_commands()
                        for cmd in commands:
                            if (
                                not route.allowed_commands
                                or cmd.name in route.allowed_commands
                            ) and cmd.name.startswith(word):
                                yield CompletionItem(
                                    text=cmd.name,
                                    metadata=cmd.description,
                                    kind="command",  # type: ignore
                                )
            else:
                # Global context completions
                ctx = self.commands.create_context(
                    self._active_context or self.global_context,
                    output_writer=context.command_context.output,
                )
                global_completion_ctx = CompletionContext(
                    document=context._document,
                    command_context=ctx,
                )
                # First try command completer if we have a word
                if word and (command := self.commands._commands.get(word)):
                    if completer := command.get_completer():
                        async for item in completer.get_completions(
                            global_completion_ctx
                        ):
                            yield item
                # Otherwise suggest commands
                else:
                    for cmd in self.commands.list_commands():
                        # In global context, only show commands not restricted to routes
                        if cmd.name.startswith(word) and not any(
                            route.allowed_commands and cmd.name in route.allowed_commands
                            for route in self._routes.values()
                        ):
                            yield CompletionItem(
                                text=cmd.name,
                                metadata=cmd.description,
                                kind="command",  # type: ignore
                            )

        except CommandError:
            # Ignore routing errors during completion
            pass

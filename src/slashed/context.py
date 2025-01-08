"""Context management for command system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

from psygnal.containers import EventedDict

from slashed.base import CommandContext
from slashed.log import get_logger


if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import UnionType

    from slashed.base import BaseCommand

logger = get_logger(__name__)
T = TypeVar("T")


@dataclass
class ContextRegistration[T]:
    """Registration of a context type."""

    context_type: type[T]
    data: T
    metadata: dict[str, Any]


class ContextRegistry:
    """Registry for managing multiple context types.

    The registry allows registering different types of context data and automatically
    matches commands to their required context based on type hints.

    Example:
        ```python
        @dataclass
        class DatabaseContext:
            connection: Any
            timeout: int = 30

        class QueryCommand(BaseCommand):
            async def execute(
                self,
                ctx: CommandContext[DatabaseContext],
                args: list[str],
                kwargs: dict[str, str]
            ) -> None:
                db = ctx.get_data()
                # Use database connection...

        registry = ContextRegistry()
        registry.register(DatabaseContext(connection="..."))
        context = registry.match_command(QueryCommand())
        ```
    """

    _COMMAND_CONTEXT_TYPE: ClassVar[type] = CommandContext

    def __init__(self) -> None:
        """Initialize an empty context registry."""
        self._contexts = EventedDict[type, ContextRegistration]()

    def register(
        self,
        data: object,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register context data.

        Args:
            data: The context data to register
            metadata: Optional metadata associated with this context

        The type of the data becomes the key for lookup.
        """
        context_type = type(data)
        self._contexts[context_type] = ContextRegistration(
            context_type=context_type,
            data=data,
            metadata=metadata or {},
        )
        logger.debug("Registered context for type: %s", context_type.__name__)

    def unregister(self, context_type: type) -> None:
        """Unregister a context type.

        Args:
            context_type: The type to unregister

        Raises:
            KeyError: If the type is not registered
        """
        if context_type not in self._contexts:
            msg = f"No context registered for type {context_type.__name__}"
            raise KeyError(msg)
        del self._contexts[context_type]
        logger.debug("Unregistered context for type: %s", context_type.__name__)

    def get[T](self, context_type: type[T]) -> T:
        """Get context data by type.

        Args:
            context_type: The type of context to get

        Returns:
            The registered context data

        Raises:
            KeyError: If no context is registered for the type
        """
        if reg := self._contexts.get(context_type):
            return reg.data
        msg = f"No context registered for type {context_type.__name__}"
        raise KeyError(msg)

    def get_registration[T](self, context_type: type[T]) -> ContextRegistration[T]:
        """Get full context registration by type.

        Args:
            context_type: The type of context to get

        Returns:
            The context registration

        Raises:
            KeyError: If no context is registered for the type
        """
        if reg := self._contexts.get(context_type):
            return reg
        msg = f"No context registered for type {context_type.__name__}"
        raise KeyError(msg)

    def list_contexts(self) -> Iterator[ContextRegistration]:
        """List all registered contexts."""
        yield from self._contexts.values()

    def _extract_context_type(
        self,
        type_hint: type | UnionType,
    ) -> type | None:
        """Extract the required context type from a type hint."""
        logger.debug("Extracting type from hint: %r", type_hint)

        # Direct CommandContext[T]
        if hasattr(type_hint, "__origin__"):
            logger.debug("Has __origin__: %r", type_hint.__origin__)  # type: ignore
            if type_hint.__origin__ is CommandContext:  # type: ignore
                args = get_args(type_hint)
                logger.debug("CommandContext args: %r", args)
                if args:
                    return args[0]

        # Union types
        origin = get_origin(type_hint)
        logger.debug("Get_origin result: %r", origin)

        if origin is not None:  # Handle any kind of union
            args = get_args(type_hint)
            logger.debug("Union args: %r", args)
            for arg in args:
                if (extracted := self._extract_context_type(arg)) is not None:
                    return extracted

        return None

    def match_command(self, command: BaseCommand) -> ContextRegistration | None:
        """Find matching context for command based on signature."""
        from typing import Union

        params = get_type_hints(command.execute)

        if "ctx" not in params:
            logger.debug("Command %s has no ctx parameter", command.name)
            return None

        # Extract required context type from type hint
        ctx_param = params["ctx"]
        # Try to extract all possible types (for unions)
        possible_types = []
        if required_type := self._extract_context_type(ctx_param):
            possible_types.append(required_type)
        if (origin := get_origin(ctx_param)) and origin is Union:
            for arg in get_args(ctx_param):
                if typ := self._extract_context_type(arg):
                    possible_types.append(typ)  # noqa: PERF401

        # Try to find a match for any of the possible types
        for required_type in possible_types:
            for reg in self._contexts.values():
                if isinstance(reg.data, required_type):
                    logger.debug(
                        "Found matching context %s for command %s",
                        reg.context_type.__name__,
                        command.name,
                    )
                    return reg

            logger.debug(
                "No matching context found for type %s (command: %s)",
                required_type.__name__,
                command.name,
            )

        return None

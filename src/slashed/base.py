"""Base interfaces for the command system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import inspect
import shlex
from typing import TYPE_CHECKING, Any, Protocol, get_type_hints

from slashed.completion import CompletionProvider
from slashed.events import CommandOutputEvent
from slashed.exceptions import CommandError


if TYPE_CHECKING:
    from slashed.store import CommandStore

type ConditionPredicate = Callable[[], bool]
type VisibilityPredicate[TContext] = Callable[[CommandContext[TContext]], bool]
type CommandFunc = Callable[..., Any] | Callable[..., Awaitable[Any]]


class OutputWriter(Protocol):
    """Interface for command output."""

    async def print(self, message: str) -> None:
        """Write a message to output."""
        ...


@dataclass
class CommandContext[TData]:
    """Context passed to command handlers.

    Type Parameters:
        TData: Type of the data available to commands. Access via get_data()
               for type-safe operations.
    """

    output: OutputWriter
    data: TData | None
    command_store: CommandStore
    metadata: dict[str, Any] = field(default_factory=dict)

    async def print(self, message: str) -> None:
        """Write a message to output."""
        self.command_store.output.emit(message)
        if self.command_store.event_handler:
            event = CommandOutputEvent(context=self, output=message)
            await self.command_store.event_handler(event)
        await self.output.print(message)

    def get_data(self) -> TData:
        """deprecated: Use context instead."""
        return self.context

    @property
    def context(self) -> TData:
        """Get context data, asserting it's not None.

        Returns:
            The context data

        Raises:
            RuntimeError: If data is None
        """
        if self.data is None:
            msg = "Context data is None"
            raise RuntimeError(msg)
        return self.data


@dataclass
class ParsedCommandArgs:
    """Arguments parsed from a command string."""

    args: list[str]
    kwargs: dict[str, str]


@dataclass
class ParsedCommand:
    """Complete parsed command."""

    name: str
    args: ParsedCommandArgs


type ExecuteFunc = Callable[[CommandContext[Any], list[str], dict[str, str]], Awaitable[None]]


class BaseCommand(ABC):
    """Abstract base class for commands."""

    name: str
    """Command name"""

    description: str
    """Command description"""

    category: str
    """Command category"""

    usage: str | None
    """Command usage"""

    _help_text: str | None
    """Optional help text"""

    def is_available(self) -> bool:
        """Check if command is currently available.

        Override or use condition predicate to implement dynamic availability.
        """
        return True

    def is_visible(self, ctx: CommandContext[Any]) -> bool:
        """Check if command should be visible in command listings.

        Override to implement context-dependent visibility. This is called
        when listing commands to filter which ones should be shown to the user.

        Args:
            ctx: The command context, providing access to context data

        Returns:
            True if command should be listed, False to hide it
        """
        return True

    def get_completer(self) -> CompletionProvider | None:
        """Get completion provider for this command.

        Returns:
            CompletionProvider if command supports completion, None otherwise
        """
        return None

    def format_usage(self) -> str | None:
        """Format usage string."""
        if not self.usage:
            return None
        return f"Usage: /{self.name} {self.usage}"

    @property
    def help_text(self) -> str:
        """Get help text, falling back to description if not set."""
        return self._help_text or self.description

    @abstractmethod
    async def execute(
        self, ctx: CommandContext[Any], args: list[str], kwargs: dict[str, str]
    ) -> Any:
        """Execute the command with parsed arguments."""
        ...


class Command[TContext = Any](BaseCommand):
    """Concrete command that can be created directly.

    Type Parameters:
        TContext: Type of the context data. Defaults to Any for flexibility.
                  Use explicit type parameter for type-safe commands.

    Example:
        ```python
        # Untyped command (backward compatible)
        cmd = Command(my_func, name="test")

        # Typed command with context data type
        cmd: Command[MyContext] = Command(
            my_func,
            name="test",
        )
        ```
    """

    _execute_func: CommandFunc
    _visible: VisibilityPredicate[TContext] | None

    def __init__(
        self,
        execute_func: CommandFunc,
        *,
        name: str | None = None,
        description: str | None = None,
        category: str = "general",
        usage: str | None = None,
        help_text: str | None = None,
        completer: CompletionProvider | Callable[[], CompletionProvider] | None = None,
        condition: ConditionPredicate | None = None,
        visible: VisibilityPredicate[TContext] | None = None,
    ) -> None:
        """Initialize command.

        Args:
            execute_func: Function to execute command
            name: Optional command name (defaults to function name)
            description: Command description (defaults to function docstring)
            category: Command category
            usage: Optional usage string (auto-generated if None)
            help_text: Optional help text (defaults to description)
            completer: Optional completion provider or factory
            condition: Optional predicate to check command availability
            visible: Optional predicate to check command visibility in listings
        """
        self.name = name or execute_func.__name__.replace("_", "-")
        self.description = description or execute_func.__doc__ or "No description"
        self.category = category
        self.usage = usage or _generate_usage(execute_func)
        self._help_text = help_text or self.description
        self._execute_func = execute_func
        self._completer = completer
        self._condition = condition
        self._visible = visible

    def is_available(self) -> bool:
        """Check if command is available based on condition."""
        if self._condition is not None:
            return self._condition()
        return True

    def is_visible(self, ctx: CommandContext[TContext]) -> bool:
        """Check if command should be visible based on visibility predicate."""
        if self._visible is not None:
            return self._visible(ctx)
        return True

    async def execute(
        self,
        ctx: CommandContext[TContext],
        args: list[str] | None = None,
        kwargs: dict[str, str] | None = None,
    ) -> Any:
        """Execute the command using provided function."""
        args = args or []
        kwargs = kwargs or {}

        call_args = parse_args(self._execute_func, ctx, args, kwargs)
        result = self._execute_func(*call_args, **kwargs)

        if inspect.isawaitable(result):
            return await result
        return result

    def get_completer(self) -> CompletionProvider | None:
        """Get completion provider."""
        match self._completer:
            case None:
                return None
            case CompletionProvider() as completer:
                return completer
            case Callable() as factory:
                return factory()
            case _:
                typ = type(self._completer)
                msg = f"Completer must be CompletionProvider or callable, not {typ}"
                raise TypeError(msg)


def _generate_usage(func: Callable[..., Any]) -> str:
    """Generate usage string from function signature."""
    usage_params = extract_usage_params(func)
    return " ".join(usage_params)


def extract_usage_params(func: Callable[..., Any], *, skip_first: bool = False) -> list[str]:
    """Extract usage parameters from a function's signature.

    Args:
        func: The function to extract usage from
        skip_first: If True, skip the first parameter (for methods with 'self')
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.items())

    if skip_first and params:
        params = params[1:]

    # Check if first parameter is a context
    if params and _is_context_param(params[0][0], func):
        params = params[1:]

    usage_params = []
    for name, param in params:
        if param.default == inspect.Parameter.empty:
            usage_params.append(f"<{name}>")
        else:
            usage_params.append(f"[--{name} <value>]")
    return usage_params


def parse_args(
    func: Callable[..., Any],
    ctx: CommandContext[Any],
    args: list[str],
    kwargs: dict[str, str],
    *,
    skip_first: bool = False,
) -> list[str | CommandContext[Any]]:
    """Parse parameters and return a list of positional arguments.

    Args:
        func: The function to parse arguments for
        ctx: The command context
        args: Positional arguments from command line
        kwargs: Keyword arguments from command line
        skip_first: If True, skip the first parameter (for methods with 'self')

    Returns:
        List of positional arguments to pass to the function
    """
    sig = inspect.signature(func)
    params_list = list(sig.parameters.items())
    if skip_first and params_list:
        params_list = params_list[1:]
    parameters = dict(params_list)

    # Check if we need to pass context
    param_names = list(parameters.keys())
    has_ctx = param_names and _is_context_param(param_names[0], func)

    # Prepare parameters for matching, excluding context if present
    if has_ctx:
        ctx_param_name = param_names[0]
        parameters_for_matching = {k: v for k, v in parameters.items() if k != ctx_param_name}
        call_args: list[str | CommandContext[Any]] = [ctx]
    else:
        parameters_for_matching = parameters
        call_args = []

    # Get required and optional parameters in order
    param_list = list(parameters_for_matching.items())
    required = [name for name, param in param_list if param.default == inspect.Parameter.empty]

    # Check for too many positional arguments
    max_positional = len(param_list)
    if len(args) > max_positional:
        param_names_list = [name for name, _ in param_list]
        msg = (
            f"Too many positional arguments. Expected at most {max_positional} "
            f"({param_names_list}), got {len(args)}"
        )
        raise CommandError(msg)

    # Check for conflicts between positional and keyword arguments
    positional_param_names = [name for name, _ in param_list[: len(args)]]
    conflicts = set(positional_param_names) & set(kwargs.keys())
    if conflicts:
        msg = f"Arguments provided both positionally and as keywords: {list(conflicts)}"
        raise CommandError(msg)

    # Check if required args are provided either as positional or keyword
    missing = [
        name for idx, name in enumerate(required) if name not in kwargs and len(args) < idx + 1
    ]

    if missing:
        msg = f"Missing required arguments: {missing}"
        raise CommandError(msg)

    # Validate keyword arguments exist in signature
    for name in kwargs:
        if name not in parameters_for_matching:
            msg = f"Unknown argument: {name}"
            raise CommandError(msg)

    # Add positional arguments
    call_args.extend(args)
    return call_args


def _is_context_param(param_name: str, func: Callable[..., Any] | None = None) -> bool:
    """Determine if a parameter is likely a context parameter.

    Uses type hints if available, falls back to name-based detection.
    """
    if func is not None:
        try:
            if param_name in (hints := get_type_hints(func)):
                hint = hints[param_name]
                # Check if type is CommandContext or a subclass/generic of it
                origin = getattr(hint, "__origin__", hint)
                if origin is CommandContext or (
                    isinstance(origin, type) and issubclass(origin, CommandContext)
                ):
                    return True
        except (TypeError, AttributeError, NameError):
            # Handle cases where type hints can't be resolved
            pass

    # Fall back to name-based detection
    return param_name in ("ctx", "context")


def parse_command(cmd_str: str) -> ParsedCommand:
    """Parse command string into name and arguments.

    Args:
        cmd_str: Command string without leading slash

    Returns:
        Parsed command with name and arguments

    Raises:
        CommandError: If command syntax is invalid
    """
    try:
        parts = shlex.split(cmd_str)
    except ValueError as e:
        msg = f"Invalid command syntax: {e}"
        raise CommandError(msg) from e

    if not parts:
        msg = "Empty command"
        raise CommandError(msg)

    name = parts[0]
    args = []
    kwargs = {}

    i = 1
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            if i + 1 < len(parts):
                kwargs[part[2:]] = parts[i + 1]
                i += 2
            else:
                msg = f"Missing value for argument: {part}"
                raise CommandError(msg)
        else:
            args.append(part)
            i += 1
    args_obj = ParsedCommandArgs(args=args, kwargs=kwargs)
    return ParsedCommand(name=name, args=args_obj)


if __name__ == "__main__":
    import asyncio

    from slashed import CommandStore, SlashedCommand

    async def command_example() -> None:
        async def test(ctx: CommandContext[Any], args: Any, kwargs: Any) -> None:
            print(f"Testing with {args} and {kwargs}")

        cmd = Command(test, name="test_fn")
        store = CommandStore()
        store.register_command(cmd)
        result = await store.execute_command_with_context(
            "test_fn --a 1 --b 2", output_writer=print
        )
        print(result)

    async def slashedcommand_example() -> None:
        def test(ctx: CommandContext[Any], a: str, b: str) -> None:
            print(f"Testing with {a} and {b}")

        class TestCommand(SlashedCommand):
            name = "test_fn"

            async def execute_command(self, ctx: CommandContext[None], a: str, b: str) -> None:
                print(f"Testing with {a} and {b}")

        store = CommandStore()
        store.register_command(TestCommand)
        result = await store.execute_command_with_context(
            "test_fn --a 1 --b 2",
            output_writer=print,
        )
        print(result)

    asyncio.run(slashedcommand_example())

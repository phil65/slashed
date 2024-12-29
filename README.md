# Slashed

[![PyPI License](https://img.shields.io/pypi/l/slashed.svg)](https://pypi.org/project/slashed/)
[![Package status](https://img.shields.io/pypi/status/slashed.svg)](https://pypi.org/project/slashed/)
[![Daily downloads](https://img.shields.io/pypi/dd/slashed.svg)](https://pypi.org/project/slashed/)
[![Weekly downloads](https://img.shields.io/pypi/dw/slashed.svg)](https://pypi.org/project/slashed/)
[![Monthly downloads](https://img.shields.io/pypi/dm/slashed.svg)](https://pypi.org/project/slashed/)
[![Distribution format](https://img.shields.io/pypi/format/slashed.svg)](https://pypi.org/project/slashed/)
[![Wheel availability](https://img.shields.io/pypi/wheel/slashed.svg)](https://pypi.org/project/slashed/)
[![Python version](https://img.shields.io/pypi/pyversions/slashed.svg)](https://pypi.org/project/slashed/)
[![Implementation](https://img.shields.io/pypi/implementation/slashed.svg)](https://pypi.org/project/slashed/)
[![Releases](https://img.shields.io/github/downloads/phil65/slashed/total.svg)](https://github.com/phil65/slashed/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/slashed)](https://github.com/phil65/slashed/graphs/contributors)
[![Github Discussions](https://img.shields.io/github/discussions/phil65/slashed)](https://github.com/phil65/slashed/discussions)
[![Github Forks](https://img.shields.io/github/forks/phil65/slashed)](https://github.com/phil65/slashed/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/slashed)](https://github.com/phil65/slashed/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/slashed)](https://github.com/phil65/slashed/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/slashed)](https://github.com/phil65/slashed/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/slashed)](https://github.com/phil65/slashed/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/slashed)](https://github.com/phil65/slashed)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/slashed)](https://github.com/phil65/slashed/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/slashed)](https://github.com/phil65/slashed/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/slashed)](https://github.com/phil65/slashed)
[![Github commits this week](https://img.shields.io/github/commit-activity/w/phil65/slashed)](https://github.com/phil65/slashed)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/slashed)](https://github.com/phil65/slashed)
[![Github commits this year](https://img.shields.io/github/commit-activity/y/phil65/slashed)](https://github.com/phil65/slashed)
[![Package status](https://codecov.io/gh/phil65/slashed/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/slashed/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyUp](https://pyup.io/repos/github/phil65/slashed/shield.svg)](https://pyup.io/repos/github/phil65/slashed/)

[Read the documentation!](https://phil65.github.io/slashed/)

A Python library for implementing slash commands with rich autocompletion support.

## Features

- Simple command registration system
- Rich autocompletion support with multiple providers
- Type-safe command and context handling:
  - Generic typing for context data
  - Type-checked command parameters
  - Safe data access patterns
- Built-in completers for:
  - File paths
  - Choice lists
  - Keyword arguments
  - Multi-value inputs
  - Callback based lists
  - Environment variables
- Extensible completion provider system
- Modern Python features (requires Python 3.12+)
- UI framework integration:
  - Textual support
  - prompt_toolkit support
- Built-in help system


**Slashed** could be compared to cmd2, both providing interactive command systems with completion and history support,
but **Slashed** offers a modern async-first design with rich (generic) type hints, improved autocompletion,
and flexible UI framework integration for both terminal (prompt-toolkit) and TUI (Textual) applications.
Unlike cmd2's tight coupling to its own REPL, **Slashed** is framework-agnostic and provides multiple ways to define commands,
making it more adaptable to different application needs while maintaining a clean, type-safe API.

## Installation

```bash
pip install slashed
```

## Quick Example

```python
from dataclasses import dataclass
from slashed import SlashedCommand, CommandStore, CommandContext
from slashed.completers import ChoiceCompleter


# Define app state that will be available to commands
@dataclass
class AppState:
    greeting_count: int = 0


# Define a command with explicit parameters and typed context
class GreetCommand(SlashedCommand):
    """Greet someone with a custom greeting."""

    name = "greet"
    category = "demo"

    async def execute_command(
        self,
        ctx: CommandContext[AppState],
        name: str = "World",
        greeting: str = "Hello",
    ):
        """Greet someone.

        Args:
            ctx: Command context
            name: Who to greet
            greeting: Custom greeting to use
        """
        state = ctx.get_data()  # Type-safe access to app state
        state.greeting_count += 1
        await ctx.output.print(
            f"{greeting}, {name}! "
            f"(Greeted {state.greeting_count} times)"
        )

    def get_completer(self) -> ChoiceCompleter:
        """Provide name suggestions."""
        return ChoiceCompleter({
            "World": "Default greeting target",
            "Everyone": "Greet all users",
            "Team": "Greet the team"
        })

# Create store and register the command
store = CommandStore()
store.register_command(GreetCommand)

# Create context with app state
ctx = store.create_context(data=AppState())

# Execute a command
await store.execute_command("greet Phil --greeting Hi", ctx)
```

## Command Definition Styles

Slashed offers two different styles for defining commands, each with its own advantages:

### Traditional Style (using Command class)

```python
from slashed import Command, CommandContext

async def add_worker(ctx: CommandContext, args: list[str], kwargs: dict[str, str]):
    """Add a worker to the pool."""
    worker_id = args[0]
    host = kwargs.get("host", "localhost")
    port = kwargs.get("port", "8080")
    await ctx.output.print(f"Adding worker {worker_id} at {host}:{port}")

cmd = Command(
    name="add-worker",
    description="Add a worker to the pool",
    execute_func=add_worker,
    usage="<worker_id> --host <host> --port <port>",
    category="workers",
)
```

#### Advantages:
- Quick to create without inheritance
- All configuration in one place
- Easier to create commands dynamically
- More flexible for simple commands
- Familiar to users of other command frameworks

### Declarative Style (using SlashedCommand)

```python
from slashed import SlashedCommand, CommandContext

class AddWorkerCommand(SlashedCommand):
    """Add a worker to the pool."""

    name = "add-worker"
    category = "workers"

    async def execute_command(
        self,
        ctx: CommandContext,
        worker_id: str,          # required parameter
        host: str = "localhost", # optional with default
        port: int = 8080,       # optional with default
    ):
        """Add a new worker to the pool.

        Args:
            ctx: Command context
            worker_id: Unique worker identifier
            host: Worker hostname
            port: Worker port number
        """
        await ctx.output.print(f"Adding worker {worker_id} at {host}:{port}")
```

#### Advantages:
- Type-safe parameter handling
- Automatic usage generation from parameters
- Help text generated from docstrings
- Better IDE support with explicit parameters
- More maintainable for complex commands
- Validates required parameters automatically
- Natural Python class structure
- Parameters are self-documenting

### When to Use Which?

Use the **traditional style** when:
- Creating simple commands with few parameters
- Generating commands dynamically
- Wanting to avoid class boilerplate
- Need maximum flexibility

Use the **declarative style** when:
- Building complex commands with many parameters
- Need type safety and parameter validation
- Want IDE support for parameters
- Documentation is important
- Working in a larger codebase

### Alternative Registration Methods

#### Using the Command Decorator

```python
@store.command(
    category="tools",
    usage="<pattern> [--type type]",
    completer=PathCompleter(files=True),
    condition=lambda: find_spec("sqlalchemy") is not None,
)
async def search(ctx: CommandContext, pattern: str, *, type: str = "any"):
    """Search for files in current directory."""
    await ctx.output.print(f"Searching for {pattern}")
```

#### Using add_command

```python
# Direct function
store.add_command(
    "search",
    search_func,
    category="tools",
    completer=PathCompleter(files=True),
)

# Import path
store.add_command(
    "query",
    "myapp.commands.database.execute_query",
    category="database",
    condition=lambda: find_spec("sqlalchemy") is not None,
)
```

#### Using CommandRegistry

For cases where you need to define commands before initializing the store (e.g., in module-level code),
you can use `CommandRegistry` to collect commands and register them later:

```python
# commands.py
from slashed import CommandRegistry
from slashed.completers import PathCompleter

registry = CommandRegistry()

@registry.command(
    category="tools",
    completer=PathCompleter(files=True)
)
async def search(ctx: CommandContext, pattern: str):
    """Search for files in current directory."""
    await ctx.output.print(f"Searching for {pattern}")

@registry.command(
    category="tools",
    condition=lambda: find_spec("sqlalchemy") is not None
)
async def query(ctx: CommandContext, sql: str):
    """Execute database query."""
    await ctx.output.print(f"Running query: {sql}")

# app.py
from slashed import CommandStore
from .commands import registry

store = CommandStore()
registry.register_to(store)  # Register all collected commands
```


## Generic Context Example

```python
from dataclasses import dataclass
from slashed import Command, CommandStore, CommandContext


# Define your custom context data
@dataclass
class AppContext:
    user_name: str
    is_admin: bool


# Command that uses the typed context
async def admin_cmd(
    ctx: CommandContext[AppContext],
    args: list[str],
    kwargs: dict[str, str],
):
    """Admin-only command."""
    state = ctx.get_data()  # Type-safe access to context data
    if not state.is_admin:
        await ctx.output.print("Sorry, admin access required!")
        return
    await ctx.output.print(f"Welcome admin {state.user_name}!")


# Create and register the command
admin_command = Command(
    name="admin",
    description="Admin-only command",
    execute_func=admin_cmd,
    category="admin",
)

# Setup the store with typed context
store = CommandStore()
store.register_command(admin_command)

# Create context with your custom data
ctx = store.create_context(
    data=AppContext(user_name="Alice", is_admin=True)
)

# Execute command with typed context
await store.execute_command("admin", ctx)
```

## UI Integration Examples

Slashed provides integrations for both prompt_toolkit and Textual:

### Prompt Toolkit REPL

```python
from prompt_toolkit import PromptSession
from slashed import CommandStore
from slashed.prompt_toolkit_completer import PromptToolkitCompleter


async def main():
    """Run a simple REPL with command completion."""
    # Initialize command store
    store = CommandStore()
    await store.initialize()

    # Create session with command completion
    completer = PromptToolkitCompleter(store=store)
    session = PromptSession(completer=completer, complete_while_typing=True)

    print("Type /help to list commands. Press Ctrl+D to exit.")

    while True:
        try:
            text = await session.prompt_async(">>> ")
            if text.startswith("/"):
                await store.execute_command_with_context(text[1:])
        except EOFError:  # Ctrl+D
            break

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Textual App

```python
from dataclasses import dataclass

from slashed import ChoiceCompleter, SlashedCommand
from slashed.textual_adapter import SlashedApp
from textual.containers import Container, VerticalScroll
from textual.widgets import Input, Label


@dataclass
class AppState:
    """Application state available to commands."""
    user_name: str


class GreetCommand(SlashedCommand):
    """Greet someone."""
    name = "greet"
    category = "demo"

    async def execute_command(self, ctx: CommandContext[AppState], name: str = "World"):
        state = ctx.get_data()
        await ctx.output.print(f"Hello, {name}! (from {state.user_name})")

    def get_completer(self) -> ChoiceCompleter:
        return ChoiceCompleter({"World": "Everyone", "Team": "The Team"})


class DemoApp(SlashedApp[AppState, None]):
    """App with slash commands and completion."""

    def compose(self) -> ComposeResult:
        # Command input with completion
        suggester = self.get_suggester()
        yield Container(Input(id="command-input", suggester=suggester))
        # Output areas
        yield VerticalScroll(id="main-output")
        yield Label(id="status")

        # Connect outputs to widgets
        self.bind_output("main", "#main-output", default=True)
        self.bind_output("status", "#status")


if __name__ == "__main__":
    state = AppState(user_name="Admin")
    app = DemoApp(data=state, commands=[GreetCommand])
    app.run()
```

Both integrations support:
- Command completion
- Command history
- Typed context data
- Rich output formatting


## Documentation

For full documentation including advanced usage and API reference, visit [phil65.github.io/slashed](https://phil65.github.io/slashed).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Make sure to read our contributing guidelines first.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

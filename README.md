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
- Built-in completers for:
  - File paths
  - Environment variables
  - Choice lists
  - Keyword arguments
  - Multi-value inputs
- Extensible completion provider system
- Type-safe with comprehensive type hints
- Modern Python features (3.12+)
- Built-in help system

## Installation

```bash
pip install slashed
```

## Quick Example

```python
from slashed import SlashedCommand, CommandStore, CommandContext
from slashed.completers import ChoiceCompleter

# Define a command with explicit parameters
class GreetCommand(SlashedCommand):
    """Greet someone with a custom greeting."""

    name = "greet"
    category = "demo"

    async def execute_command(
        self,
        ctx: CommandContext,
        name: str = "World",
        greeting: str = "Hello",
    ) -> None:
        """Greet someone.

        Args:
            ctx: Command context
            name: Who to greet
            greeting: Custom greeting to use
        """
        await ctx.output.print(f"{greeting}, {name}!")

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

# Create context and execute a command
ctx = store.create_context(data=None)
await store.execute_command("greet Phil --greeting Hi", ctx)
```

## Command Definition Styles

Slashed offers two different styles for defining commands, each with its own advantages:

### Traditional Style (using Command class)

```python
from slashed import Command, CommandContext

async def add_worker(ctx: CommandContext, args: list[str], kwargs: dict[str, str]) -> None:
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
    ) -> None:
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
) -> None:
    if not ctx.data.is_admin:
        await ctx.output.print("Sorry, admin access required!")
        return
    await ctx.output.print(f"Welcome admin {ctx.data.user_name}!")


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

## Documentation

For full documentation including advanced usage and API reference, visit [slashed.readthedocs.io](https://phil65.github.io/slashed).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Make sure to read our contributing guidelines first.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

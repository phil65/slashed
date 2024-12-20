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
from slashed import Command, CommandStore, CommandContext
from slashed.completers import ChoiceCompleter

# Create a command store
store = CommandStore()

# Define a command with completion support
async def greet(ctx: CommandContext, args: list[str], kwargs: dict[str, str]) -> None:
    name = args[0] if args else "World"
    greeting = kwargs.get("greeting", "Hello")
    await ctx.output.print(f"{greeting}, {name}!")

greet_cmd = Command(
    name="greet",
    description="Greet someone",
    execute_func=greet,
    usage="[name] --greeting <greeting>",
    help_text="Greet someone with a custom greeting.\n\nExample: /greet Phil --greeting Hi",
    category="demo",
    completer=ChoiceCompleter({
        "World": "Default greeting target",
        "Everyone": "Greet all users",
        "Team": "Greet the team"
    })
)

# Register the command
store.register_command(greet_cmd)

# Register built-in commands (help, etc)
store.register_builtin_commands()

# Create context and execute a command
ctx = store.create_context(data=None)
await store.execute_command("greet Phil --greeting Hi", ctx)
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

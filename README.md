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


A simple Python library for implementing slash commands with autocompletion support.

## Features

- Simple command registration system
- Rich autocompletion support
- Built-in file path and environment variable completion
- Extensible completion provider system
- Type-safe with full type hints
- Modern Python features (3.12+)

## Installation

```bash
pip install slashed
```

## Quick Example

```python
from slashed import Command, CommandStore, CommandContext
from slashed.output import DefaultOutputWriter

# Create a command store
store = CommandStore()

# Define a simple command
async def hello(ctx: CommandContext, args: list[str], kwargs: dict[str, str]) -> None:
    name = args[0] if args else "World"
    await ctx.output.print(f"Hello, {name}!")

hello_cmd = Command(
    name="hello",
    description="Say hello",
    execute_func=hello,
    usage="[name]"
)

# Register the command
store.register_command(hello_cmd)

# Create output writer
output = DefaultOutputWriter()

# Execute a command
await store.execute_command("hello Phil", CommandContext(output=output, data=None))
```

## Documentation

For full documentation, visit [slashed.readthedocs.io](https://phil65.github.io/slashed).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

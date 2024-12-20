"""Command-related exceptions."""


class CommandError(Exception):
    """Base exception for command-related errors."""


class ExitCommandError(CommandError):
    """Special exception to signal clean Session exit."""

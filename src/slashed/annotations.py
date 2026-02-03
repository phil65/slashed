"""Annotations for command parameters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Short:
    """Marker for parameter shorthand.

    Use with Annotated to define single-character shortcuts for command parameters.

    Example:
        ```python
        from typing import Annotated
        from slashed import SlashedCommand, Short

        class MyCommand(SlashedCommand):
            name = "greet"

            async def execute_command(
                self,
                name: str,
                verbose: Annotated[bool, Short("v")] = False,
                output: Annotated[str, Short("o")] = "stdout",
            ):
                ...
        ```

        Now the command can be invoked as:
        - `/greet John --verbose true`
        - `/greet John -v true`
        - `/greet John -o file.txt -v true`
    """

    char: str
    """Single character shorthand (without the dash)."""

    def __post_init__(self) -> None:
        """Validate the shorthand character."""
        if len(self.char) != 1:
            msg = f"Short must be a single character, got: {self.char!r}"
            raise ValueError(msg)
        if not self.char.isalpha():
            msg = f"Short must be an alphabetic character, got: {self.char!r}"
            raise ValueError(msg)

"""Example showing Slashed integration with prompt_toolkit."""

from __future__ import annotations

import asyncio

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.patch_stdout import patch_stdout

from slashed.output import DefaultOutputWriter
from slashed.prompt_toolkit_completion import PromptToolkitCompleter
from slashed.store import CommandStore


class PromptOutputWriter(DefaultOutputWriter):
    """Output writer that works with prompt_toolkit's patch_stdout."""

    async def print(self, message: str) -> None:
        """Print message using prompt_toolkit's print function."""
        from prompt_toolkit import print_formatted_text

        if self._console is not None:
            # Get string with ANSI codes, strip extra newlines
            with self._console.capture() as capture:
                self._console.print(message, end="")  # Prevent extra newline from print
            rendered = capture.get()
            print_formatted_text(ANSI(rendered))
        else:
            print_formatted_text(message)


async def main() -> None:
    """Run the example REPL."""
    # Initialize command store and context
    store = CommandStore()
    await store.initialize()

    context = store.create_context(
        data=None, output_writer=PromptOutputWriter(force_terminal=True)
    )

    # Create prompt session with our completer
    session = PromptSession(
        completer=PromptToolkitCompleter(
            commands=store._commands, command_context=context
        ),
        complete_while_typing=True,
    )

    # Run the REPL
    print("Type /help to list commands. Press Ctrl+D to exit.")

    with patch_stdout():
        while True:
            try:
                # Get input with prompt
                text = await session.prompt_async(">>> ")

                if text.startswith("/"):
                    # Execute command without slash
                    await store.execute_command(text[1:], context)
                else:
                    print(f"Echo: {text}")

            except EOFError:  # Ctrl+D
                break
            except KeyboardInterrupt:  # Ctrl+C
                continue
            except Exception as e:  # noqa: BLE001
                print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

"""Shell executor for bash-like command lines with pipes and chaining.

This module provides execution of command lines with shell semantics:
- Pipes: cmd1 | cmd2 | cmd3
- AND chaining: cmd1 && cmd2
- OR chaining: cmd1 || cmd2
- Sequential: cmd1 ; cmd2

Uses bashlex for parsing the command line into an AST.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import bashlex  # type: ignore[import-untyped]
import bashlex.ast  # type: ignore[import-untyped]

from slashed.base import CommandResult
from slashed.exceptions import CommandError


if TYPE_CHECKING:
    from slashed.base import CommandContext
    from slashed.store import CommandStore


class ShellExecutor:
    """Executes bash-like command lines with pipes and chaining.

    This executor handles shell syntax like pipes (|), AND (&&), OR (||),
    and sequential (;) operators. It delegates individual command execution
    to the CommandStore.

    Example:
        ```python
        executor = ShellExecutor(store)
        result = await executor.execute("cat file.txt | grep error", ctx)
        ```
    """

    def __init__(self, store: CommandStore) -> None:
        """Initialize the shell executor.

        Args:
            store: Command store for resolving and executing commands
        """
        self.store = store

    async def execute(
        self,
        command_line: str,
        ctx: CommandContext[Any],
    ) -> CommandResult:
        """Execute a full command line (may have pipes, &&, ||, etc.).

        Args:
            command_line: The command line to execute
            ctx: Command context

        Returns:
            Result of the command line execution
        """
        try:
            parts = bashlex.parse(command_line)
        except bashlex.errors.ParsingError as e:  # pyright: ignore[reportAttributeAccessIssue]
            return CommandResult(stderr=f"Parse error: {e}", exit_code=1)

        if not parts:
            return CommandResult()

        # Execute each top-level part (usually just one)
        result = CommandResult()
        for part in parts:
            result = await self._execute_node(part, ctx)

        return result

    async def _execute_node(
        self,
        node: bashlex.ast.node,
        ctx: CommandContext[Any],
    ) -> CommandResult:
        """Execute an AST node.

        Args:
            node: The AST node to execute
            ctx: Command context

        Returns:
            Result of execution
        """
        match node.kind:  # pyright: ignore[reportAttributeAccessIssue]
            case "command":
                return await self._execute_command(node, ctx)
            case "pipeline":
                return await self._execute_pipeline(node, ctx)
            case "list":
                return await self._execute_list(node, ctx)
            case "compound":
                # For now, don't support compound commands (if/for/while)
                return CommandResult(
                    stderr="Compound commands (if/for/while) not supported",
                    exit_code=1,
                )
            case _:
                return CommandResult(
                    stderr=f"Unknown node kind: {node.kind}",  # pyright: ignore[reportAttributeAccessIssue]
                    exit_code=1,
                )

    async def _execute_command(
        self,
        node: bashlex.ast.node,
        ctx: CommandContext[Any],
    ) -> CommandResult:
        """Execute a simple command node.

        Args:
            node: Command AST node
            ctx: Command context

        Returns:
            Result of command execution
        """
        # Extract words from the command (skip redirections, assignments for now)
        words: list[str] = []
        for part in node.parts:  # pyright: ignore[reportAttributeAccessIssue]
            if part.kind == "word":  # pyright: ignore[reportAttributeAccessIssue]
                words.append(part.word)  # pyright: ignore[reportAttributeAccessIssue]
            elif part.kind == "redirect":
                # TODO: Handle redirections
                pass
            elif part.kind == "assignment":  # pyright: ignore[reportAttributeAccessIssue]
                # TODO: Handle assignments
                pass

        if not words:
            return CommandResult()

        cmd_name = words[0]
        raw_args = words[1:]
        # Get the command
        command = self.store.get_command(cmd_name)
        if not command:
            stderr = f"Unknown command: {cmd_name}"
            return CommandResult(stderr=stderr, exit_code=127)  # std "command not found" exit code
        # Parse arguments into positional args and kwargs
        # bashlex already did the shell parsing, now we just need to
        # separate --flag value pairs from positional arguments
        args: list[str] = []
        kwargs: dict[str, str] = {}
        i = 0
        while i < len(raw_args):
            arg = raw_args[i]
            if arg.startswith("--") and i + 1 < len(raw_args):
                # Long flag: --name value
                kwargs[arg[2:]] = raw_args[i + 1]
                i += 2
            elif arg.startswith("-") and len(arg) == 2 and arg[1].isalpha():  # noqa: PLR2004
                # Short flag: -x value
                if i + 1 < len(raw_args):
                    kwargs[arg[1:]] = raw_args[i + 1]
                    i += 2
                else:
                    args.append(arg)
                    i += 1
            else:
                args.append(arg)
                i += 1

        # Execute with stdin from context
        try:
            result = await command.execute(ctx, args, kwargs)
            return _normalize_result(result)
        except CommandError as e:
            return CommandResult(stderr=str(e), exit_code=1)
        except Exception as e:  # noqa: BLE001
            return CommandResult(stderr=f"Error: {e}", exit_code=1)

    async def _execute_pipeline(
        self,
        node: bashlex.ast.node,
        ctx: CommandContext[Any],
    ) -> CommandResult:
        """Execute a pipeline (cmd1 | cmd2 | cmd3).

        Args:
            node: Pipeline AST node
            ctx: Command context

        Returns:
            Result of the last command in pipeline
        """
        # Extract commands from pipeline (skip pipe operators)
        commands = [p for p in node.parts if p.kind == "command"]  # pyright: ignore[reportAttributeAccessIssue]
        if not commands:
            return CommandResult()

        # Execute pipeline, threading stdout through stdin
        current_stdin = ctx.stdin
        result = CommandResult()
        for i, cmd in enumerate(commands):
            # Create context with current stdin
            pipe_ctx = replace(ctx, stdin=current_stdin)
            # Execute command
            result = await self._execute_command(cmd, pipe_ctx)
            # If not the last command, use stdout as next stdin
            if i < len(commands) - 1:
                current_stdin = result.stdout
                # Clear stdout for intermediate commands (only last command's stdout matters)
                # But we keep stderr accumulated
            else:
                # Last command - its stdout is the pipeline's stdout
                pass

        return result

    async def _execute_list(
        self,
        node: bashlex.ast.node,
        ctx: CommandContext[Any],
    ) -> CommandResult:
        """Execute a list (cmd1 && cmd2 || cmd3 ; cmd4).

        Unlike pipelines where stdout flows between commands, in a list
        each command's stdout is accumulated in the final result.

        Args:
            node: List AST node
            ctx: Command context

        Returns:
            Combined result with accumulated stdout/stderr
        """
        accumulated_stdout: list[str] = []
        accumulated_stderr: list[str] = []
        result = CommandResult()
        pending_operator: str | None = None

        for part in node.parts:  # pyright: ignore[reportAttributeAccessIssue]
            if part.kind == "operator":  # pyright: ignore[reportAttributeAccessIssue]
                pending_operator = part.op  # pyright: ignore[reportAttributeAccessIssue]
            elif part.kind in ("command", "pipeline"):
                # Check if we should execute based on previous result and operator
                should_execute = True

                if pending_operator == "&&":
                    # Only execute if previous succeeded
                    should_execute = result.exit_code == 0
                elif pending_operator == "||":
                    # Only execute if previous failed
                    should_execute = result.exit_code != 0
                # For ";" or None, always execute

                if should_execute:
                    if part.kind == "command":  # pyright: ignore[reportAttributeAccessIssue]
                        result = await self._execute_command(part, ctx)
                    else:
                        result = await self._execute_pipeline(part, ctx)

                    # Accumulate output
                    if result.stdout:
                        accumulated_stdout.append(result.stdout)
                    if result.stderr:
                        accumulated_stderr.append(result.stderr)

                pending_operator = None

        # Return combined result
        return CommandResult(
            stdout="".join(accumulated_stdout),
            stderr="".join(accumulated_stderr),
            exit_code=result.exit_code,  # Exit code of last executed command
        )


def _normalize_result(result: Any) -> CommandResult:
    """Normalize command return value to CommandResult.

    Args:
        result: Return value from command execution

    Returns:
        Normalized CommandResult
    """
    if result is None:
        return CommandResult()
    if isinstance(result, CommandResult):
        return result
    if isinstance(result, str):
        return CommandResult(stdout=result)
    if isinstance(result, int):
        return CommandResult(exit_code=result)
    # For other types, convert to string
    return CommandResult(stdout=str(result))

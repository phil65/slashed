# AGENTS.md

## Overview

`slashed` is a framework-agnostic, async-first library for slash commands with typed
argument parsing and pluggable autocompletion. Commands are defined as functions
(`Command`) or classes (`SlashedCommand`), collected in a `CommandStore`, and executed with a
typed `CommandContext[T]`. Optional adapters integrate with Textual and prompt_toolkit.
Python >= 3.14, package in `src/slashed/`.

## Architecture

- `src/slashed/base.py`: core types. `CommandContext[TData]` (output writer, user data,
  store, metadata; `ctx.print()`, `ctx.get_data()`), `BaseCommand` (ABC), `Command` (wraps a
  callable, auto-generates usage from its signature), `CommandResult`, `OutputWriter`
  protocol, and argument parsing: `parse_command()`, `parse_args()` (type coercion from
  annotations, `Short` shorthand flags, context-param detection).
- `src/slashed/commands.py`: `SlashedCommand`, the declarative base. Subclasses set
  `name`/`category` and implement `execute_command(self, ctx, ...)`; parameters become CLI args.
- `src/slashed/store.py`: `CommandStore`, the central registry and executor. Registration
  (`register_command`, `add_command`, `@store.command`), execution (`execute_command`,
  `execute_command_with_context`, `execute_command_auto`, `execute_shell*`), history, typed
  context registry, builtin/system commands (`initialize()` / `register_builtin_commands`).
  psygnal signals: `command_executed`, `output`, `command_events` (an `EventedDict`).
- `src/slashed/registry.py`: `CommandRegistry`, collects decorated functions at import time,
  `register_to(store)` later.
- `src/slashed/context.py`: `ContextRegistry`, type-based context matching. Finds the
  registered context whose type matches the `ctx: CommandContext[T]` annotation of a command.
- `src/slashed/router.py`: `CommandRouter[TGlobal, TRoute]`, `@prefix` routing to per-route
  contexts with allowed-command sets and `temporary_context()`.
- `src/slashed/shell_executor.py`: `ShellExecutor`, bashlex-based parsing of `&&`, `||`, `;`
  and pipes across slash commands.
- `src/slashed/completion.py`: `CompletionItem`, `CompletionContext`, `CompletionProvider`
  (ABC), `CommandCompleter`. `src/slashed/completers.py`: built-in providers (`PathCompleter`,
  `ChoiceCompleter`, `KeywordCompleter`, `MultiValueCompleter`, `EnvVarCompleter`,
  `ChainedCompleter`, `CallbackCompleter`).
- `src/slashed/output.py`: `DefaultOutputWriter` (rich if installed), `QueueOutputWriter`,
  `CallbackOutputWriter`, `TransformOutputWriter`.
- `src/slashed/events.py`: event dataclasses emitted by the store.
- `src/slashed/builtin/`: `help_cmd.py` (help, exit) and `system.py` (exec, run, processes,
  sysinfo, kill, env; needs `psutil`, only registered with `enable_system_commands=True`).
- `src/slashed/textual_adapter/`: `SlashedApp` (`app.py`), `CommandInput`, `CommandTextArea`,
  `SlashedSuggester`; `dropdown.py` (`CommandDropdown`) is internal.
- `src/slashed/prompt_toolkit_completer.py`: `PromptToolkitCompleter`.
- `src/slashed_examples/`: runnable demo apps (not shipped in the wheel).

Flow: input string -> `parse_command` -> `CommandStore.get_command` -> `BaseCommand.execute`
-> `parse_args` binds args to the function / `execute_command` signature -> output via the
context's `OutputWriter` -> `command_executed` / `output` signals.

## Where to look

| Task | Location |
|------|----------|
| Argument parsing, type coercion, usage strings | `src/slashed/base.py` |
| Declarative command behaviour | `src/slashed/commands.py` |
| Registration, execution, history, signals | `src/slashed/store.py` |
| Automatic context matching | `src/slashed/context.py` |
| `@route` handling | `src/slashed/router.py` |
| Pipes / `&&` / `||` | `src/slashed/shell_executor.py` |
| New completer | `src/slashed/completers.py` |
| Completion kinds (`CompletionKind` literal) | `src/slashed/slashed_types.py` |
| Help / system commands | `src/slashed/builtin/` |
| Textual widgets | `src/slashed/textual_adapter/` |
| Public exports | `src/slashed/__init__.py` |
| Tests | `tests/test_*.py` |

## Commands

```bash
uv sync --all-extras                 # setup (default groups: dev, lint, docs)
uv run pytest                        # tests (asyncio_mode = "auto")
uv run ruff check . && uv run ruff format --check .
uv run ty check                      # type check (src only); warnings fail CI
uv run deptry src                    # dependency declaration check
uv run mknodes build                 # docs (README + auto-generated API pages)
duty lint | lint_check | test | build | serve  # duties.py; duty is not a project dependency
```

CI (`.github/workflows/build.yml`) runs ruff check, ruff format --check, `ty check` and pytest
on Linux/macOS/Windows with Python 3.13 and 3.14 (3.14 is allowed to fail). Docs are built by
`.github/workflows/documentation.yml` on pushes to main.

## Conventions

- Modern Python (3.14): PEP 695 generics, `match`, no `from __future__ import annotations` (PEP 649; banned via ruff TID251).
- Google-style docstrings without types in `Args`.
- Tests are plain pytest functions (no classes); async tests need no marker.
- Ruff with preview formatting; Markdown code blocks (README) are formatted too.
- Type ignores: use targeted `# ty: ignore[rule]` only for real checker limitations
  (e.g. the untyped bashlex AST).
- Context matching and `parse_args` read runtime type hints: annotations of command
  callables must be resolvable at runtime (module-level classes, real imports for types used in
  `ctx: CommandContext[T]`).

## Pitfalls

- Copier-managed (template `copier-phil65`): `.github/workflows/*`, `.pre-commit-config.yaml`,
  `duties.py`, `mkdocs.yml`, most of `pyproject.toml`. Don't hand-edit template-owned parts; add
  dependencies below the `# Only add below (Copier)` markers.
- Optional dependencies: `slashed[textual]` (textual, prompt-toolkit, rich),
  `slashed[prompt-toolkit]`, `slashed[system_commands]` (psutil). Core `import slashed` must not
  import them; adapters import them at module level.
- Command strings passed to `execute_command*` have no leading `/`.
- `help`/`exit` are only available after `await store.initialize()` (or
  `register_builtin_commands()`).
- System commands execute arbitrary processes; disabled unless `enable_system_commands=True`.
- `uv.lock` is gitignored.

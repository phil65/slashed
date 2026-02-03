"""Tests for parse_args function, especially VAR_POSITIONAL (*args) handling."""

from __future__ import annotations

from typing import Annotated

import pytest

from slashed.annotations import Short
from slashed.base import CommandContext, parse_args, parse_command
from slashed.exceptions import CommandError
from slashed.store import CommandStore


@pytest.fixture
def store() -> CommandStore:
    """Fixture providing command store."""
    return CommandStore()


@pytest.fixture
def context(store: CommandStore) -> CommandContext[None]:
    """Fixture providing command context."""
    return store.create_context(None)


# Module-level test functions for shorthand tests
# (needed because get_type_hints requires proper __globals__)
def _shorthand_func_basic(name: str, verbose: Annotated[bool, Short("v")] = False):
    pass


def _shorthand_func_multiple(
    verbose: Annotated[bool, Short("v")] = False,
    output: Annotated[str, Short("o")] = "stdout",
):
    pass


def _shorthand_func_with_context(ctx: CommandContext, verbose: Annotated[bool, Short("v")] = False):
    pass


def _shorthand_func_int(count: Annotated[int, Short("c")] = 1):
    pass


class TestParseArgsBasic:
    """Basic parse_args tests."""

    def test_no_args(self, context: CommandContext):
        """Test function with no arguments."""

        def func():
            pass

        call_args, call_kwargs = parse_args(func, context, [], {})
        assert call_args == []
        assert call_kwargs == {}

    def test_simple_positional(self, context: CommandContext):
        """Test function with simple positional args."""

        def func(name: str, value: str):
            pass

        call_args, call_kwargs = parse_args(func, context, ["alice", "bob"], {})
        assert call_args == ["alice", "bob"]
        assert call_kwargs == {}

    def test_simple_keyword(self, context: CommandContext):
        """Test function with keyword args."""

        def func(name: str, value: str = "default"):
            pass

        call_args, call_kwargs = parse_args(func, context, ["alice"], {"value": "custom"})
        assert call_args == ["alice"]
        assert call_kwargs == {"value": "custom"}

    def test_with_context_param(self, context: CommandContext):
        """Test function that takes context as first param."""

        def func(ctx: CommandContext, name: str):
            pass

        call_args, call_kwargs = parse_args(func, context, ["alice"], {})
        assert call_args[0] is context
        assert call_args[1] == "alice"
        assert call_kwargs == {}

    def test_missing_required_arg(self, context: CommandContext):
        """Test error when required arg is missing."""

        def func(name: str, value: str):
            pass

        with pytest.raises(CommandError, match="Missing required arguments"):
            parse_args(func, context, ["alice"], {})

    def test_too_many_positional_args(self, context: CommandContext):
        """Test error when too many positional args provided."""

        def func(name: str):
            pass

        with pytest.raises(CommandError, match="Too many positional arguments"):
            parse_args(func, context, ["alice", "bob", "charlie"], {})

    def test_unknown_kwarg(self, context: CommandContext):
        """Test error when unknown kwarg provided."""

        def func(name: str):
            pass

        with pytest.raises(CommandError, match="Unknown argument: unknown"):
            parse_args(func, context, ["alice"], {"unknown": "value"})

    def test_conflict_positional_and_keyword(self, context: CommandContext):
        """Test error when same arg provided positionally and as keyword."""

        def func(name: str, value: str):
            pass

        with pytest.raises(
            CommandError, match="Arguments provided both positionally and as keywords"
        ):
            parse_args(func, context, ["alice", "bob"], {"name": "charlie"})


class TestParseArgsVarPositional:
    """Tests for VAR_POSITIONAL (*args) handling - the bug we fixed."""

    def test_var_positional_simple(self, context: CommandContext):
        """Test function with *args collects extra positional args."""

        def func(*nodes: str):
            pass

        call_args, call_kwargs = parse_args(func, context, ["a", "b", "c"], {})
        assert call_args == ["a", "b", "c"]
        assert call_kwargs == {}

    def test_var_positional_with_keyword_only(self, context: CommandContext):
        """Test *args followed by keyword-only param - the main bug case."""

        def func(*nodes: str, name: str):
            pass

        # This was the failing case: alice, bob should go to *nodes, name via kwarg
        call_args, call_kwargs = parse_args(func, context, ["alice", "bob"], {"name": "crew"})
        assert call_args == ["alice", "bob"]
        assert call_kwargs == {"name": "crew"}

    def test_var_positional_with_keyword_only_default(self, context: CommandContext):
        """Test *args with keyword-only param that has default."""

        def func(*nodes: str, name: str = "default"):
            pass

        call_args, call_kwargs = parse_args(func, context, ["a", "b"], {})
        assert call_args == ["a", "b"]
        assert call_kwargs == {}

    def test_var_positional_missing_required_keyword_only(self, context: CommandContext):
        """Test error when required keyword-only param is missing."""

        def func(*nodes: str, name: str):
            pass

        with pytest.raises(CommandError, match=r"Missing required arguments.*name"):
            parse_args(func, context, ["alice", "bob"], {})

    def test_var_positional_with_context(self, context: CommandContext):
        """Test context + *args + keyword-only."""

        def func(ctx: CommandContext, *nodes: str, name: str):
            pass

        call_args, call_kwargs = parse_args(func, context, ["alice", "bob"], {"name": "crew"})
        assert call_args[0] is context
        assert call_args[1:] == ["alice", "bob"]
        assert call_kwargs == {"name": "crew"}

    def test_var_positional_with_regular_param_before(self, context: CommandContext):
        """Test regular param + *args + keyword-only."""

        def func(first: str, *rest: str, name: str):
            pass

        call_args, call_kwargs = parse_args(func, context, ["a", "b", "c"], {"name": "test"})
        # first="a" goes to first param, b, c go to *rest
        assert call_args == ["a", "b", "c"]
        assert call_kwargs == {"name": "test"}

    def test_var_positional_no_conflict_with_keyword_only(self, context: CommandContext):
        """Positional args should NOT conflict with keyword-only params."""

        def func(*nodes: str, name: str):
            pass

        # "name" is keyword-only, so providing positional args should NOT
        # raise a conflict error even if we provide many args
        call_args, call_kwargs = parse_args(func, context, ["a", "b", "c", "d"], {"name": "test"})
        assert call_args == ["a", "b", "c", "d"]
        assert call_kwargs == {"name": "test"}

    def test_var_positional_empty(self, context: CommandContext):
        """Test *args with no positional args provided."""

        def func(*nodes: str, name: str = "default"):
            pass

        call_args, call_kwargs = parse_args(func, context, [], {})
        assert call_args == []
        assert call_kwargs == {}

    def test_var_positional_with_multiple_keyword_only(self, context: CommandContext):
        """Test *args with multiple keyword-only params."""

        def func(*items: str, name: str, count: int = 1):
            pass

        call_args, call_kwargs = parse_args(
            func, context, ["a", "b"], {"name": "test", "count": "5"}
        )
        assert call_args == ["a", "b"]
        assert call_kwargs == {"name": "test", "count": 5}


class TestParseArgsVarKeyword:
    """Tests for VAR_KEYWORD (**kwargs) handling."""

    def test_var_keyword_simple(self, context: CommandContext):
        """Test function with **kwargs accepts any keyword args."""

        def func(**kwargs: str):
            pass

        call_args, call_kwargs = parse_args(func, context, [], {"a": "1", "b": "2"})
        assert call_args == []
        assert call_kwargs == {"a": "1", "b": "2"}

    def test_var_positional_and_keyword(self, context: CommandContext):
        """Test function with both *args and **kwargs."""

        def func(*args: str, **kwargs: str):
            pass

        call_args, call_kwargs = parse_args(func, context, ["a", "b"], {"x": "1", "y": "2"})
        assert call_args == ["a", "b"]
        assert call_kwargs == {"x": "1", "y": "2"}


class TestParseArgsTypeCoercion:
    """Tests for type coercion in parse_args."""

    def test_int_coercion(self, context: CommandContext):
        """Test integer type coercion."""

        def func(count: int):
            pass

        call_args, _call_kwargs = parse_args(func, context, ["42"], {})
        assert call_args == [42]
        assert isinstance(call_args[0], int)

    def test_float_coercion(self, context: CommandContext):
        """Test float type coercion."""

        def func(value: float):
            pass

        call_args, _call_kwargs = parse_args(func, context, ["3.14"], {})
        assert call_args == [3.14]
        assert isinstance(call_args[0], float)

    def test_bool_coercion(self, context: CommandContext):
        """Test boolean type coercion."""

        def func(flag: bool):
            pass

        call_args, _call_kwargs = parse_args(func, context, ["true"], {})
        assert call_args == [True]

        call_args, _call_kwargs = parse_args(func, context, ["false"], {})
        assert call_args == [False]

    def test_kwarg_coercion(self, context: CommandContext):
        """Test type coercion for keyword args."""

        def func(name: str, count: int = 1):
            pass

        _call_args, call_kwargs = parse_args(func, context, ["test"], {"count": "10"})
        assert call_kwargs == {"count": 10}
        assert isinstance(call_kwargs["count"], int)

    def test_keyword_only_coercion_with_var_positional(self, context: CommandContext):
        """Test type coercion for keyword-only params after *args."""

        def func(*items: str, count: int):
            pass

        call_args, call_kwargs = parse_args(func, context, ["a", "b"], {"count": "5"})
        assert call_args == ["a", "b"]
        assert call_kwargs == {"count": 5}
        assert isinstance(call_kwargs["count"], int)


class TestShorthandArgs:
    """Tests for shorthand argument support via Annotated[..., Short(...)]."""

    def test_shorthand_expansion(self, context: CommandContext):
        """Test that -v expands to --verbose when Short('v') is used."""
        call_args, call_kwargs = parse_args(_shorthand_func_basic, context, ["test"], {"v": "true"})
        assert call_args == ["test"]
        assert call_kwargs == {"verbose": True}

    def test_shorthand_multiple(self, context: CommandContext):
        """Test multiple shorthand parameters."""
        call_args, call_kwargs = parse_args(
            _shorthand_func_multiple, context, [], {"v": "true", "o": "file.txt"}
        )
        assert call_args == []
        assert call_kwargs == {"verbose": True, "output": "file.txt"}

    def test_shorthand_with_long_form(self, context: CommandContext):
        """Test that long form still works alongside shorthand definition."""
        call_args, call_kwargs = parse_args(
            _shorthand_func_basic, context, ["test"], {"verbose": "true"}
        )
        assert call_args == ["test"]
        assert call_kwargs == {"verbose": True}

    def test_shorthand_conflict_error(self, context: CommandContext):
        """Test error when both shorthand and long form provided."""
        with pytest.raises(CommandError, match="provided both as '-v' and '--verbose'"):
            parse_args(_shorthand_func_basic, context, [], {"v": "true", "verbose": "false"})

    def test_shorthand_with_context(self, context: CommandContext):
        """Test shorthand works with context parameter."""
        call_args, call_kwargs = parse_args(
            _shorthand_func_with_context, context, [], {"v": "true"}
        )
        assert call_args[0] is context
        assert call_kwargs == {"verbose": True}

    def test_shorthand_with_positional(self, context: CommandContext):
        """Test shorthand works with positional arguments."""
        call_args, call_kwargs = parse_args(_shorthand_func_basic, context, ["test"], {"v": "true"})
        assert call_args == ["test"]
        assert call_kwargs == {"verbose": True}

    def test_shorthand_type_coercion(self, context: CommandContext):
        """Test that type coercion works with shorthand."""
        call_args, call_kwargs = parse_args(_shorthand_func_int, context, [], {"c": "42"})
        assert call_kwargs == {"count": 42}
        assert isinstance(call_kwargs["count"], int)

    def test_no_shorthand_single_char_passes_through(self, context: CommandContext):
        """Test that single-char kwargs without Short annotation pass through."""

        def func(**kwargs):
            pass

        # No Short annotation, so "v" stays as "v"
        call_args, call_kwargs = parse_args(func, context, [], {"v": "value"})
        assert call_kwargs == {"v": "value"}


class TestParseCommandShorthand:
    """Tests for shorthand parsing in parse_command."""

    def test_parse_short_flag(self):
        """Test that -x value is parsed correctly."""
        parsed = parse_command("cmd -v true")
        assert parsed.name == "cmd"
        assert parsed.args.args == []
        assert parsed.args.kwargs == {"v": "true"}

    def test_parse_multiple_short_flags(self):
        """Test multiple short flags."""
        parsed = parse_command("cmd -v true -o output.txt")
        assert parsed.name == "cmd"
        assert parsed.args.kwargs == {"v": "true", "o": "output.txt"}

    def test_parse_mixed_short_and_long(self):
        """Test mixing short and long form arguments."""
        parsed = parse_command("cmd -v true --output file.txt")
        assert parsed.name == "cmd"
        assert parsed.args.kwargs == {"v": "true", "output": "file.txt"}

    def test_parse_short_with_positional(self):
        """Test short flags with positional arguments."""
        parsed = parse_command("cmd arg1 -v true arg2")
        assert parsed.name == "cmd"
        assert parsed.args.args == ["arg1", "arg2"]
        assert parsed.args.kwargs == {"v": "true"}

    def test_parse_short_missing_value(self):
        """Test error when short flag missing value."""
        with pytest.raises(CommandError, match="Missing value for argument: -v"):
            parse_command("cmd -v")

    def test_parse_numeric_not_short_flag(self):
        """Test that -1 is treated as positional, not a flag."""
        parsed = parse_command("cmd -1")
        assert parsed.args.args == ["-1"]
        assert parsed.args.kwargs == {}

    def test_parse_long_dash_not_short_flag(self):
        """Test that multi-char after dash is positional."""
        parsed = parse_command("cmd -abc")
        assert parsed.args.args == ["-abc"]
        assert parsed.args.kwargs == {}

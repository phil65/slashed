"""Tests for parse_args function, especially VAR_POSITIONAL (*args) handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from slashed.base import parse_args
from slashed.exceptions import CommandError
from slashed.store import CommandStore


if TYPE_CHECKING:
    from slashed.base import CommandContext


@pytest.fixture
def store() -> CommandStore:
    """Fixture providing command store."""
    return CommandStore()


@pytest.fixture
def context(store: CommandStore) -> CommandContext[None]:
    """Fixture providing command context."""
    return store.create_context(None)


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

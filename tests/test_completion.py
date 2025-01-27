from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest

from slashed.completers import KeywordCompleter, MultiValueCompleter
from slashed.completion import CompletionContext, CompletionItem, CompletionProvider


class TestCompleter(CompletionProvider):
    async def get_completions(
        self, context: CompletionContext
    ) -> AsyncIterator[CompletionItem]:
        yield CompletionItem(text="test")
        yield CompletionItem(text="test2")


@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.text = "test"
    doc.cursor_position = 4
    doc.get_word_before_cursor.return_value = "test"
    return doc


@pytest.mark.asyncio
async def test_basic_completer(mock_document):
    completer = TestCompleter()
    context = CompletionContext[Any](document=mock_document)

    items = []
    async for item in completer.get_completions(context):
        items.append(item)  # noqa: PERF401

    assert len(items) == 2  # noqa: PLR2004
    assert items[0].text == "test"
    assert items[1].text == "test2"


@pytest.mark.asyncio
async def test_multi_value_completer(mock_document):
    base_completer = TestCompleter()
    multi_completer = MultiValueCompleter(base_completer, delimiter=",")

    # Test single value completion
    mock_document.text = "te"
    mock_document.get_word_before_cursor.return_value = "te"
    context = CompletionContext[Any](document=mock_document)

    items = []
    async for item in multi_completer.get_completions(context):
        items.append(item)  # noqa: PERF401

    assert len(items) == 2  # noqa: PLR2004
    assert items[0].text == "test"
    assert items[1].text == "test2"

    # Test completion with existing value
    mock_document.text = "value1, te"
    mock_document.get_word_before_cursor.return_value = "te"
    context = CompletionContext[Any](document=mock_document)

    items = []
    async for item in multi_completer.get_completions(context):
        items.append(item)

    assert len(items) == 2  # noqa: PLR2004
    assert items[0].text == "value1, test"
    assert items[1].text == "value1, test2"


@pytest.mark.asyncio
async def test_keyword_completer(mock_document):
    keywords = {"param1": "First parameter", "param2": "Second parameter"}
    value_completer = TestCompleter()
    completer = KeywordCompleter(keywords, value_completer)

    # Test keyword completion
    mock_document.text = "--"
    mock_document.get_word_before_cursor.return_value = "--"
    context = CompletionContext[Any](document=mock_document)

    items = [item async for item in completer.get_completions(context)]
    assert len(items) == 2  # noqa: PLR2004
    assert all(item.text.startswith("--") for item in items)
    assert {"--param1", "--param2"} == {item.text for item in items}

    # Test value completion
    mock_document.text = "--param1 t"
    mock_document.get_word_before_cursor.return_value = "t"
    context = CompletionContext[Any](document=mock_document)
    context._args = ["--param1", "t"]
    context._arg_position = 1

    items = []
    async for item in completer.get_completions(context):
        items.append(item)

    assert len(items) == 2  # noqa: PLR2004
    assert {"test", "test2"} == {item.text for item in items}


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])

"""Tests for the checkpointer factory — memory, SQLite, and env-based selection."""

import os

from langgraph.checkpoint.memory import MemorySaver

from openhypothesis.state.checkpoint import create_checkpointer


def test_create_checkpointer_defaults_to_memory() -> None:
    saver = create_checkpointer()
    assert isinstance(saver, MemorySaver)


def test_create_checkpointer_memory_explicit() -> None:
    saver = create_checkpointer(":memory:")
    assert isinstance(saver, MemorySaver)


def test_create_checkpointer_from_env() -> None:
    os.environ["OPENHYPOTHESIS_DB"] = ":memory:"
    saver = create_checkpointer()
    assert isinstance(saver, MemorySaver)
    del os.environ["OPENHYPOTHESIS_DB"]

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


def create_checkpointer(db_url: str | None = None) -> "BaseCheckpointSaver[Any]":
    """Factory: return a LangGraph checkpointer based on the DB URL.

    Resolution order:
      1. Explicit ``db_url`` argument.
      2. ``OPENHYPOTHESIS_DB`` environment variable.
      3. Fall back to in-memory (``MemorySaver``).

    Supported URL schemes:
      - ``:memory:`` or empty → ``MemorySaver``
      - ``postgres://...`` → ``PostgresSaver`` (requires psycopg + langgraph-checkpoint-postgres)
      - any other path → ``SqliteSaver`` (local SQLite file)
    """
    env_url: str = db_url or ""
    if not env_url:
        env_url = os_getenv("OPENHYPOTHESIS_DB", "")
    if env_url.startswith("postgres"):
        return _create_postgres_saver(env_url)
    if env_url and env_url != ":memory:":
        return _create_sqlite_saver(env_url)
    return MemorySaver()


def os_getenv(key: str, default: str = "") -> str:
    """Wrapper around ``os.getenv`` to avoid module-level side effects during import."""
    import os

    return os.getenv(key, default)


def _create_sqlite_saver(path: str) -> "BaseCheckpointSaver[Any]":
    """Create a SQLite-based checkpointer from a file path.

    Uses ``check_same_thread=False`` so the connection can be shared across
    LangGraph's async event loop threads.
    """
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    conn = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(conn)


def _create_postgres_saver(url: str) -> "BaseCheckpointSaver[Any]":
    """Create a Postgres-based checkpointer. Raises a helpful error if deps missing."""
    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        conn = psycopg.connect(url)
        return PostgresSaver(conn)  # type: ignore[no-any-return]
    except ImportError:
        raise RuntimeError(
            "PostgresSaver requires 'psycopg' and 'langgraph-checkpoint-postgres'. "
            "Install with: uv add psycopg langgraph-checkpoint-postgres"
        ) from None

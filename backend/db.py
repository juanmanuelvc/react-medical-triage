from typing import Any

import aiosqlite

from core.config import settings

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS triage_sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    steps_json  TEXT NOT NULL DEFAULT '[]',
    result_json TEXT NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL
)
"""


async def init_db(path: str | None = None) -> None:
    """Create the triage_sessions table if it does not already exist.

    Args:
        path: Optional SQLite file path. Defaults to ``settings.db_path``.
              Pass an explicit path in tests to avoid touching the real database.
    """
    async with aiosqlite.connect(path or settings.db_path) as db:
        await db.execute(_CREATE_TABLE)
        await db.commit()


async def insert_session(session_id: str, created_at: str, path: str | None = None) -> None:
    """Insert a new session row with status ``running``.

    Args:
        session_id: UUID string used as the primary key.
        created_at: ISO-8601 timestamp string.
        path: Optional SQLite file path override (for tests).
    """
    async with aiosqlite.connect(path or settings.db_path) as db:
        await db.execute(
            "INSERT INTO triage_sessions (id, created_at, status) VALUES (?, ?, 'running')",
            (session_id, created_at),
        )
        await db.commit()


async def update_session(
    session_id: str,
    steps_json: str,
    result_json: str,
    status: str,
    path: str | None = None,
) -> None:
    """Update steps, result, and status for an existing session.

    Args:
        session_id: UUID of the session to update.
        steps_json: JSON-serialised list of ReActStepSchema dicts.
        result_json: JSON-serialised TriageResponse (``"{}"`` for error sessions).
        status: New status value — ``"complete"`` or ``"error"``.
        path: Optional SQLite file path override (for tests).
    """
    async with aiosqlite.connect(path or settings.db_path) as db:
        await db.execute(
            "UPDATE triage_sessions SET steps_json=?, result_json=?, status=? WHERE id=?",
            (steps_json, result_json, status, session_id),
        )
        await db.commit()


async def get_session(session_id: str, path: str | None = None) -> dict[str, Any] | None:
    """Fetch a session row by ID.

    Args:
        session_id: UUID of the session to retrieve.
        path: Optional SQLite file path override (for tests).

    Returns:
        A dict of column values, or ``None`` if no row with that ID exists.
    """
    async with aiosqlite.connect(path or settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM triage_sessions WHERE id=?", (session_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None

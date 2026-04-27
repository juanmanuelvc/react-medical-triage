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
    async with aiosqlite.connect(path or settings.db_path) as db:
        await db.execute(_CREATE_TABLE)
        await db.commit()


async def insert_session(session_id: str, created_at: str, path: str | None = None) -> None:
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
    async with aiosqlite.connect(path or settings.db_path) as db:
        await db.execute(
            "UPDATE triage_sessions SET steps_json=?, result_json=?, status=? WHERE id=?",
            (steps_json, result_json, status, session_id),
        )
        await db.commit()


async def get_session(session_id: str, path: str | None = None) -> dict[str, Any] | None:
    async with aiosqlite.connect(path or settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM triage_sessions WHERE id=?", (session_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None

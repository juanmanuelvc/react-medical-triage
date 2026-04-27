from pathlib import Path

import aiosqlite
import pytest

from db import get_session, init_db, insert_session, update_session


@pytest.fixture
async def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


async def test_init_db_creates_table(tmp_path: Path) -> None:
    path = str(tmp_path / "test.db")
    await init_db(path)
    async with aiosqlite.connect(path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='triage_sessions'"
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None


async def test_insert_session_status_is_running(db_path: str) -> None:
    await insert_session("sess-1", "2026-04-22T10:00:00", db_path)
    row = await get_session("sess-1", db_path)
    assert row is not None
    assert row["id"] == "sess-1"
    assert row["status"] == "running"


async def test_update_session_persists_result(db_path: str) -> None:
    await insert_session("sess-2", "2026-04-22T10:00:00", db_path)
    await update_session("sess-2", "[]", '{"session_id":"sess-2"}', "complete", db_path)
    row = await get_session("sess-2", db_path)
    assert row is not None
    assert row["status"] == "complete"
    assert row["result_json"] == '{"session_id":"sess-2"}'


async def test_get_session_returns_none_for_missing(db_path: str) -> None:
    row = await get_session("nonexistent", db_path)
    assert row is None

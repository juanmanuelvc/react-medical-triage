import json
from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agent.react_loop import ReActStep, TriageResult
from api.main import app

_MOCK_STEP = ReActStep(
    step_number=0,
    step_type="tool_call",
    tool_name="symptom_ner",
    tool_args={"text": "chest pain"},
    tool_result={"diseases": ["chest pain"]},
    reasoning=None,
    tokens_prompt=100,
    tokens_completion=50,
    tokens_cached=0,
    latency_ms=123.0,
)


async def _fake_run_triage(
    symptoms_text: str,
    session_id: str,
    on_step: Callable[[ReActStep], Coroutine[Any, Any, None]] | None = None,
) -> TriageResult:
    if on_step:
        await on_step(_MOCK_STEP)
    return TriageResult(
        session_id=session_id,
        steps=[_MOCK_STEP],
        recommendation="Seek immediate care.",
        urgency_level="immediate",
        confidence=0.9,
        red_flags=["chest pain"],
        reasoning_summary="Acute chest pain identified.",
    )


@pytest.fixture
def mock_deps(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    sessions: dict[str, Any] = {}

    async def fake_init_db() -> None:
        pass

    async def fake_insert(session_id: str, created_at: str) -> None:
        sessions[session_id] = {"status": "running", "steps_json": "[]", "result_json": "{}"}

    async def fake_update(session_id: str, steps_json: str, result_json: str, status: str) -> None:
        sessions[session_id].update(
            {"status": status, "steps_json": steps_json, "result_json": result_json}
        )

    async def fake_get(session_id: str) -> dict[str, Any] | None:
        return sessions.get(session_id)

    monkeypatch.setattr("api.main.init_db", fake_init_db)
    monkeypatch.setattr("api.routers.triage.insert_session", fake_insert)
    monkeypatch.setattr("api.routers.triage.update_session", fake_update)
    monkeypatch.setattr("api.routers.triage.get_session", fake_get)
    monkeypatch.setattr("api.routers.triage.run_triage", _fake_run_triage)
    return sessions


async def _collect_sse_events(response: Any) -> list[dict[str, Any]]:
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


async def test_post_triage_streams_step_then_result(mock_deps: dict[str, Any]) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/triage", json={"symptoms": "chest pain"}) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            events = await _collect_sse_events(resp)

    assert len(events) == 2
    assert events[0]["event"] == "step"
    assert events[0]["data"]["tool_name"] == "symptom_ner"
    assert events[1]["event"] == "result"
    assert events[1]["data"]["urgency_level"] == "immediate"


async def test_post_triage_missing_symptoms_returns_422(mock_deps: dict[str, Any]) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/triage", json={})
    assert resp.status_code == 422


async def test_get_triage_session_found(mock_deps: dict[str, Any]) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/triage", json={"symptoms": "headache"}) as resp:
            events = await _collect_sse_events(resp)
        session_id = events[-1]["data"]["session_id"]

        resp = await client.get(f"/triage/{session_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["urgency_level"] == "immediate"


async def test_get_triage_session_not_found(mock_deps: dict[str, Any]) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/triage/nonexistent-id")
    assert resp.status_code == 404


async def test_get_triage_session_not_complete_returns_404(mock_deps: dict[str, Any]) -> None:
    mock_deps["in-progress-id"] = {"status": "running", "steps_json": "[]", "result_json": "{}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/triage/in-progress-id")
    assert resp.status_code == 404


async def test_post_triage_exception_emits_error_event(
    mock_deps: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def raising_run_triage(
        symptoms_text: str,
        session_id: str,
        on_step: Any = None,
    ) -> None:
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("api.routers.triage.run_triage", raising_run_triage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/triage", json={"symptoms": "chest pain"}) as resp:
            events = await _collect_sse_events(resp)

    assert len(events) == 1
    assert events[0]["event"] == "error"
    assert any(s["status"] == "error" for s in mock_deps.values())

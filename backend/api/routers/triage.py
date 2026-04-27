import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent.react_loop import ReActStep, TriageResult, run_triage
from api.schemas import ReActStepSchema, TriageRequest, TriageResponse
from db import get_session, insert_session, update_session

router = APIRouter()


async def _triage_stream(symptoms: str, session_id: str) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue[ReActStep | TriageResult | BaseException] = asyncio.Queue()

    async def on_step(step: ReActStep) -> None:
        await queue.put(step)

    async def _run() -> None:
        try:
            result = await run_triage(symptoms, session_id, on_step=on_step)
            await queue.put(result)
        except Exception as exc:
            await queue.put(exc)

    task = asyncio.create_task(_run())

    while True:
        item = await queue.get()
        if isinstance(item, BaseException):
            await update_session(session_id, "[]", "{}", "error")
            yield f"data: {json.dumps({'event': 'error', 'detail': str(item)})}\n\n"
            break
        if isinstance(item, ReActStep):
            step_data = ReActStepSchema.from_step(item).model_dump()
            yield f"data: {json.dumps({'event': 'step', 'data': step_data})}\n\n"
        elif isinstance(item, TriageResult):
            response = TriageResponse.from_result(item)
            await update_session(
                session_id,
                json.dumps([s.model_dump() for s in response.steps]),
                response.model_dump_json(),
                "complete",
            )
            yield f"data: {json.dumps({'event': 'result', 'data': response.model_dump()})}\n\n"
            break

    await task


@router.post("/triage")
async def post_triage(body: TriageRequest) -> StreamingResponse:
    session_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    await insert_session(session_id, created_at)
    return StreamingResponse(
        _triage_stream(body.symptoms, session_id),
        media_type="text/event-stream",
    )


@router.get("/triage/{session_id}", response_model=TriageResponse)
async def get_triage(session_id: str) -> TriageResponse:
    row = await get_session(session_id)
    if row is None or row["status"] != "complete":
        raise HTTPException(status_code=404, detail="Session not found")
    return TriageResponse.model_validate_json(row["result_json"])

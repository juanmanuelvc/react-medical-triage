import dataclasses
from typing import Any

from pydantic import BaseModel

from agent.react_loop import ReActStep, TriageResult


class TriageRequest(BaseModel):
    symptoms: str


class ReActStepSchema(BaseModel):
    step_number: int
    step_type: str
    tool_name: str | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    reasoning: str | None
    tokens_prompt: int
    tokens_completion: int
    tokens_cached: int
    latency_ms: float

    @classmethod
    def from_step(cls, step: ReActStep) -> "ReActStepSchema":
        return cls(**dataclasses.asdict(step))


class TriageResponse(BaseModel):
    session_id: str
    steps: list[ReActStepSchema]
    recommendation: str
    urgency_level: str
    confidence: float
    red_flags: list[str]
    reasoning_summary: str

    @classmethod
    def from_result(cls, result: TriageResult) -> "TriageResponse":
        return cls(
            session_id=result.session_id,
            steps=[ReActStepSchema.from_step(s) for s in result.steps],
            recommendation=result.recommendation,
            urgency_level=result.urgency_level,
            confidence=result.confidence,
            red_flags=result.red_flags,
            reasoning_summary=result.reasoning_summary,
        )

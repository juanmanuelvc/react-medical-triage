import pytest
from pydantic import ValidationError

from api.schemas import ReActStepSchema, TriageRequest, TriageResponse


def test_triage_request_valid() -> None:
    req = TriageRequest(symptoms="chest pain and shortness of breath")
    assert req.symptoms == "chest pain and shortness of breath"


def test_triage_request_missing_symptoms_raises() -> None:
    with pytest.raises(ValidationError):
        TriageRequest()  # type: ignore[call-arg]


def test_react_step_schema_tool_call() -> None:
    step = ReActStepSchema(
        step_number=0,
        step_type="tool_call",
        tool_name="symptom_ner",
        tool_args={"text": "chest pain"},
        tool_result={"diseases": ["chest pain"]},
        reasoning=None,
        tokens_prompt=100,
        tokens_completion=50,
        tokens_cached=0,
        latency_ms=150.0,
    )
    assert step.step_number == 0
    assert step.tool_name == "symptom_ner"
    assert step.reasoning is None


def test_react_step_schema_thought() -> None:
    step = ReActStepSchema(
        step_number=1,
        step_type="thought",
        tool_name=None,
        tool_args=None,
        tool_result=None,
        reasoning="I need to check protocols.",
        tokens_prompt=80,
        tokens_completion=30,
        tokens_cached=0,
        latency_ms=90.0,
    )
    assert step.tool_name is None
    assert step.reasoning == "I need to check protocols."


def test_triage_response_valid() -> None:
    resp = TriageResponse(
        session_id="abc-123",
        steps=[],
        recommendation="Seek immediate care.",
        urgency_level="immediate",
        confidence=0.9,
        red_flags=["chest pain"],
        reasoning_summary="Acute chest pain identified.",
    )
    assert resp.urgency_level == "immediate"
    assert resp.confidence == 0.9
    assert resp.red_flags == ["chest pain"]

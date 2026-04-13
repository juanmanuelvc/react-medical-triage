import json
from unittest.mock import AsyncMock, MagicMock, patch

from agent.react_loop import MAX_STEPS, ReActStep, TriageResult, run_triage

# ---------------------------------------------------------------------------
# Mock response factories
# ---------------------------------------------------------------------------


def _make_tool_call_response(
    tool_name: str,
    args_dict: dict,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> MagicMock:
    tc = MagicMock()
    tc.id = f"call_{tool_name}"
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args_dict)

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    response.usage = usage
    return response


def _make_text_response(
    text: str,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = None

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    response.usage = usage
    return response


def _make_finish_response(
    urgency: str = "non_urgent",
    confidence: float = 0.9,
    recommendation: str = "See your GP within 48 hours.",
    red_flags: list | None = None,
    reasoning_summary: str = "No red flags found.",
) -> MagicMock:
    return _make_tool_call_response(
        "finish",
        {
            "recommendation": recommendation,
            "urgency_level": urgency,
            "confidence": confidence,
            "red_flags": red_flags or [],
            "reasoning_summary": reasoning_summary,
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_run_triage_finish_on_first_step() -> None:
    finish_resp = _make_finish_response(
        urgency="urgent",
        confidence=0.85,
        recommendation="Go to A&E immediately.",
    )
    with patch("litellm.acompletion", new=AsyncMock(return_value=finish_resp)):
        result = await run_triage("I have severe chest pain.", "session-1")

    assert isinstance(result, TriageResult)
    assert result.session_id == "session-1"
    assert result.urgency_level == "urgent"
    assert result.recommendation == "Go to A&E immediately."
    assert result.confidence == 0.85
    assert len(result.steps) == 1
    assert result.steps[0].step_type == "finish"


async def test_run_triage_tool_then_finish() -> None:
    ner_resp = _make_tool_call_response("symptom_ner", {"text": "I have a headache"})
    finish_resp = _make_finish_response(urgency="semi_urgent")

    mock_ner_tool = MagicMock()
    mock_ner_tool.execute = AsyncMock(return_value={"diseases": ["headache"], "chemicals": []})

    with (
        patch("litellm.acompletion", new=AsyncMock(side_effect=[ner_resp, finish_resp])),
        patch("agent.react_loop.TOOL_REGISTRY", {"symptom_ner": mock_ner_tool}),
    ):
        result = await run_triage("I have a headache", "session-2")

    assert len(result.steps) == 2
    assert result.steps[0].step_type == "tool_call"
    assert result.steps[0].tool_name == "symptom_ner"
    assert result.steps[0].tool_result == {"diseases": ["headache"], "chemicals": []}
    assert result.steps[1].step_type == "finish"
    assert result.urgency_level == "semi_urgent"
    mock_ner_tool.execute.assert_called_once_with(text="I have a headache")


async def test_run_triage_max_steps_exceeded() -> None:
    ner_resp = _make_tool_call_response("symptom_ner", {"text": "pain"})
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value={"diseases": [], "chemicals": []})
    mock_acompletion = AsyncMock(return_value=ner_resp)

    with (
        patch("litellm.acompletion", new=mock_acompletion),
        patch("agent.react_loop.TOOL_REGISTRY", {"symptom_ner": mock_tool}),
    ):
        result = await run_triage("I have pain.", "session-3")

    assert result.urgency_level == "immediate"
    assert result.confidence == 0.0
    assert "Escalate" in result.recommendation
    assert len(result.steps) == MAX_STEPS
    assert mock_acompletion.call_count == MAX_STEPS


async def test_run_triage_text_response_breaks_loop() -> None:
    text = "I cannot determine the urgency from the information provided."
    text_resp = _make_text_response(text)
    mock_acompletion = AsyncMock(return_value=text_resp)

    with patch("litellm.acompletion", new=mock_acompletion):
        result = await run_triage("Some vague complaint.", "session-4")

    assert mock_acompletion.call_count == 1
    assert len(result.steps) == 1
    assert result.steps[0].step_type == "thought"
    assert result.steps[0].reasoning == text
    assert result.urgency_level == "immediate"
    assert result.confidence == 0.0


async def test_run_triage_unknown_tool_returns_error() -> None:
    unknown_resp = _make_tool_call_response("nonexistent_tool", {"arg": "value"})
    finish_resp = _make_finish_response()

    with (
        patch("litellm.acompletion", new=AsyncMock(side_effect=[unknown_resp, finish_resp])),
        patch("agent.react_loop.TOOL_REGISTRY", {}),
    ):
        result = await run_triage("Some symptoms.", "session-5")

    assert result.steps[0].tool_result == {"error": "unknown tool: nonexistent_tool"}
    assert result.steps[1].step_type == "finish"
    assert isinstance(result, TriageResult)


async def test_run_triage_sets_session_id() -> None:
    finish_resp = _make_finish_response()
    with patch("litellm.acompletion", new=AsyncMock(return_value=finish_resp)):
        result = await run_triage("Mild fever.", "my-custom-session-id-xyz")

    assert result.session_id == "my-custom-session-id-xyz"


async def test_run_triage_steps_have_timing() -> None:
    finish_resp = _make_finish_response()
    with patch("litellm.acompletion", new=AsyncMock(return_value=finish_resp)):
        result = await run_triage("Sore throat.", "session-7")

    assert len(result.steps) >= 1
    for step in result.steps:
        assert isinstance(step, ReActStep)
        assert isinstance(step.latency_ms, float)
        assert step.latency_ms >= 0.0

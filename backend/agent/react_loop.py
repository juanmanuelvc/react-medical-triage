import json
import os
import time
from dataclasses import dataclass
from typing import Any

import litellm

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_REGISTRY

LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/qwen2.5-0.5B-Instruct")
LLM_API_BASE: str | None = os.getenv("LLM_API_BASE")
LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")

MAX_STEPS: int = 10

_FINISH_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": (
            "Submit the final triage recommendation. Call this when you have gathered "
            "sufficient information to orient the patient."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recommendation": {
                    "type": "string",
                    "description": "Plain-language recommendation for the patient.",
                },
                "urgency_level": {
                    "type": "string",
                    "enum": ["immediate", "urgent", "semi_urgent", "non_urgent"],
                    "description": "Triage urgency classification.",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score between 0.0 and 1.0.",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "red_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Concerning signs identified in the patient's description.",
                },
                "reasoning_summary": {
                    "type": "string",
                    "description": "Brief summary of the reasoning chain that led to this result.",
                },
            },
            "required": [
                "recommendation",
                "urgency_level",
                "confidence",
                "red_flags",
                "reasoning_summary",
            ],
        },
    },
}

_ESCALATION_RESULT_RECOMMENDATION = (
    "Escalate to medical professional — triage loop did not converge."
)
_ESCALATION_RESULT_SUMMARY = "Agent did not call finish within the allowed number of steps."


@dataclass
class ReActStep:
    step_number: int
    step_type: str  # "thought" | "tool_call" | "finish"
    tool_name: str | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    reasoning: str | None
    tokens_prompt: int
    tokens_completion: int
    latency_ms: float


@dataclass
class TriageResult:
    session_id: str
    steps: list[ReActStep]
    recommendation: str
    urgency_level: str  # "immediate" | "urgent" | "semi_urgent" | "non_urgent"
    confidence: float
    red_flags: list[str]
    reasoning_summary: str


async def run_triage(symptoms_text: str, session_id: str) -> TriageResult:
    """Run the ReAct triage loop for the given symptom description.

    Calls the LLM in a Think→Act→Observe cycle up to MAX_STEPS times.
    The loop exits when the agent calls `finish` or when MAX_STEPS is exceeded.
    """
    all_tools = [tool.to_openai_schema() for tool in TOOL_REGISTRY.values()]
    all_tools.append(_FINISH_TOOL_SCHEMA)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": symptoms_text},
    ]
    steps: list[ReActStep] = []

    for step_num in range(MAX_STEPS):
        t0 = time.monotonic()
        # TODO(tracing): wrap in OTel span with react.step_number=step_num
        response: litellm.ModelResponse = await litellm.acompletion(  # type: ignore[assignment]
            model=LLM_MODEL,
            messages=messages,
            tools=all_tools,
            tool_choice="auto",
            api_base=LLM_API_BASE,
            api_key=LLM_API_KEY,
        )
        latency_ms = (time.monotonic() - t0) * 1000

        msg = response.choices[0].message
        usage = response.usage  # type: ignore[attr-defined]
        tokens_prompt: int = usage.prompt_tokens if usage else 0
        tokens_completion: int = usage.completion_tokens if usage else 0

        if not msg.tool_calls:
            steps.append(
                ReActStep(
                    step_number=step_num,
                    step_type="thought",
                    tool_name=None,
                    tool_args=None,
                    tool_result=None,
                    reasoning=msg.content,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    latency_ms=latency_ms,
                )
            )
            break

        # Append the assistant turn (with tool_calls) before processing results.
        # The OpenAI API requires the assistant message to precede all its tool results.
        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args: dict[str, Any] = json.loads(tc.function.arguments)

            if tool_name == "finish":
                steps.append(
                    ReActStep(
                        step_number=step_num,
                        step_type="finish",
                        tool_name="finish",
                        tool_args=tool_args,
                        tool_result=None,
                        reasoning=None,
                        tokens_prompt=tokens_prompt,
                        tokens_completion=tokens_completion,
                        latency_ms=latency_ms,
                    )
                )
                return TriageResult(
                    session_id=session_id,
                    steps=steps,
                    recommendation=tool_args["recommendation"],
                    urgency_level=tool_args["urgency_level"],
                    confidence=float(tool_args["confidence"]),
                    red_flags=tool_args.get("red_flags", []),
                    reasoning_summary=tool_args["reasoning_summary"],
                )

            if tool_name not in TOOL_REGISTRY:
                tool_result: dict[str, Any] = {"error": f"unknown tool: {tool_name}"}
            else:
                tool_result = await TOOL_REGISTRY[tool_name].execute(**tool_args)

            steps.append(
                ReActStep(
                    step_number=step_num,
                    step_type="tool_call",
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_result=tool_result,
                    reasoning=None,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    latency_ms=latency_ms,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result),
                }
            )

    return TriageResult(
        session_id=session_id,
        steps=steps,
        recommendation=_ESCALATION_RESULT_RECOMMENDATION,
        urgency_level="immediate",
        confidence=0.0,
        red_flags=[],
        reasoning_summary=_ESCALATION_RESULT_SUMMARY,
    )

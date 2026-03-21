import json
from pathlib import Path

import pytest

from agent.tools.triage_protocol import TriageProtocolTool

_SAMPLE_PROTOCOLS = [
    {
        "primary_symptom": "chest_pain",
        "severity": "severe",
        "urgency_level": 1,
        "protocol_name": "Possible ACS — Emergency",
        "referral_type": "emergency",
        "rationale": "Severe chest pain may indicate AMI.",
    },
    {
        "primary_symptom": "chest_pain",
        "severity": "mild",
        "urgency_level": 3,
        "protocol_name": "Chest Pain — Routine Referral",
        "referral_type": "cardiology_outpatient",
        "rationale": "Mild atypical chest pain, outpatient review.",
    },
    {
        "primary_symptom": "fever",
        "severity": "moderate",
        "urgency_level": 2,
        "protocol_name": "Fever — Same-Day Assessment",
        "referral_type": "urgent_gp",
        "rationale": "Moderate fever requires same-day assessment.",
    },
]


@pytest.fixture
def tool(tmp_path: Path) -> TriageProtocolTool:
    protocols_file = tmp_path / "protocols.json"
    protocols_file.write_text(json.dumps(_SAMPLE_PROTOCOLS))
    return TriageProtocolTool(protocols_path=protocols_file)


def test_tool_properties(tool: TriageProtocolTool):
    assert tool.name == "triage_protocol"
    schema = tool.input_schema
    assert "primary_symptom" in schema["properties"]
    assert "severity" in schema["properties"]
    assert schema["required"] == ["primary_symptom", "severity"]


async def test_execute_known_symptom_and_severity(tool: TriageProtocolTool):
    result = await tool.execute(primary_symptom="chest_pain", severity="severe")
    assert result["urgency_level"] == 1
    assert result["referral_type"] == "emergency"
    assert result["protocol_name"] == "Possible ACS — Emergency"
    assert "rationale" in result


async def test_execute_another_protocol(tool: TriageProtocolTool):
    result = await tool.execute(primary_symptom="fever", severity="moderate")
    assert result["urgency_level"] == 2
    assert result["referral_type"] == "urgent_gp"


async def test_execute_unknown_combination_returns_error(tool: TriageProtocolTool):
    result = await tool.execute(primary_symptom="headache", severity="severe")
    assert "error" in result
    assert "No protocol found" in result["error"]


async def test_execute_missing_primary_symptom_returns_error(tool: TriageProtocolTool):
    result = await tool.execute(severity="mild")
    assert "error" in result


async def test_execute_missing_severity_returns_error(tool: TriageProtocolTool):
    result = await tool.execute(primary_symptom="chest_pain")
    assert "error" in result


async def test_execute_case_insensitive(tool: TriageProtocolTool):
    result = await tool.execute(primary_symptom="CHEST_PAIN", severity="MILD")
    assert result["urgency_level"] == 3


def test_protocols_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        TriageProtocolTool(protocols_path=Path("/nonexistent/protocols.json"))


def test_to_openai_schema(tool: TriageProtocolTool):
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "triage_protocol"

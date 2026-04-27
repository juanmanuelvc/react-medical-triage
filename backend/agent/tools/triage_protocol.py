import json
from pathlib import Path
from typing import Any

from agent.tools.base import Tool

_DEFAULT_PROTOCOLS_PATH = (
    Path(__file__).parent.parent.parent.parent / "infra" / "protocols" / "triage_protocols.json"
)


class TriageProtocolTool(Tool):
    def __init__(self, protocols_path: Path = _DEFAULT_PROTOCOLS_PATH) -> None:
        """Load triage protocols and index them by (primary_symptom, severity) for O(1) lookup.

        Args:
            protocols_path: Path to the JSON protocols file.
        """
        with protocols_path.open() as f:
            protocols: list[dict[str, Any]] = json.load(f)
        self._index: dict[tuple[str, str], dict[str, Any]] = {
            (p["primary_symptom"], p["severity"]): p for p in protocols
        }

    @property
    def name(self) -> str:
        return "triage_protocol"

    @property
    def description(self) -> str:
        return (
            "Look up the triage protocol for a given primary symptom and severity level. "
            "Returns urgency level, referral type, protocol name, and clinical rationale."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "primary_symptom": {
                    "type": "string",
                    "description": (
                        "The main presenting symptom. "
                        "One of: chest_pain, dyspnea, headache, fever, abdominal_pain, "
                        "neurological_deficit, rash, trauma."
                    ),
                },
                "severity": {
                    "type": "string",
                    "enum": ["mild", "moderate", "severe"],
                    "description": "Assessed severity of the symptom.",
                },
            },
            "required": ["primary_symptom", "severity"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        try:
            primary_symptom: str = kwargs.get("primary_symptom", "").strip().lower()
            severity: str = kwargs.get("severity", "").strip().lower()
            if not primary_symptom or not severity:
                return {"error": "primary_symptom and severity are required"}
            protocol = self._index.get((primary_symptom, severity))
            if protocol is None:
                return {
                    "error": (
                        f"No protocol found for symptom='{primary_symptom}' severity='{severity}'"
                    )
                }
            return {
                "urgency_level": protocol["urgency_level"],
                "referral_type": protocol["referral_type"],
                "protocol_name": protocol["protocol_name"],
                "rationale": protocol["rationale"],
            }
        except Exception as exc:
            return {"error": str(exc)}

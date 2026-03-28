from agent.tools.base import Tool
from agent.tools.knowledge_base import KnowledgeBaseTool
from agent.tools.symptom_ner import SymptomNERTool
from agent.tools.triage_protocol import TriageProtocolTool

TOOL_REGISTRY: dict[str, Tool] = {
    tool.name: tool
    for tool in [
        SymptomNERTool(),
        KnowledgeBaseTool(),
        TriageProtocolTool(),
    ]
}

__all__ = ["Tool", "TOOL_REGISTRY"]

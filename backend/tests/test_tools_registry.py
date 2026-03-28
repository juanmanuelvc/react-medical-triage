from agent.tools import TOOL_REGISTRY


def test_registry_contains_all_tools():
    assert "symptom_ner" in TOOL_REGISTRY
    assert "knowledge_base" in TOOL_REGISTRY
    assert "triage_protocol" in TOOL_REGISTRY


def test_registry_keys_match_tool_names():
    for key, tool in TOOL_REGISTRY.items():
        assert key == tool.name


def test_all_tools_have_openai_schema():
    for tool in TOOL_REGISTRY.values():
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "parameters" in schema["function"]

from unittest.mock import MagicMock, patch

import numpy as np


def _patch_heavy_deps():
    """Patch model-loading dependencies so the registry can be imported in tests."""
    import agent.tools.symptom_ner as ner_module

    ner_module._nlp = MagicMock(return_value=MagicMock(ents=[]))

    dim = 4
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((50, dim), dtype=np.float32)
    return mock_model


def test_registry_contains_all_tools():
    mock_model = _patch_heavy_deps()
    with patch("agent.tools.knowledge_base.SentenceTransformer", return_value=mock_model):
        from agent.tools import TOOL_REGISTRY

        assert "symptom_ner" in TOOL_REGISTRY
        assert "knowledge_base" in TOOL_REGISTRY
        assert "triage_protocol" in TOOL_REGISTRY


def test_registry_keys_match_tool_names():
    mock_model = _patch_heavy_deps()
    with patch("agent.tools.knowledge_base.SentenceTransformer", return_value=mock_model):
        from agent.tools import TOOL_REGISTRY

        for key, tool in TOOL_REGISTRY.items():
            assert key == tool.name


def test_all_tools_have_openai_schema():
    mock_model = _patch_heavy_deps()
    with patch("agent.tools.knowledge_base.SentenceTransformer", return_value=mock_model):
        from agent.tools import TOOL_REGISTRY

        for tool in TOOL_REGISTRY.values():
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "parameters" in schema["function"]

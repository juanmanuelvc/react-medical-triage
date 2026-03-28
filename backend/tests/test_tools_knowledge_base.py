import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from agent.tools.knowledge_base import KnowledgeBaseTool

_SAMPLE_CORPUS = [
    {"id": "doc_001", "title": "Chest Pain", "content": "Chest pain may indicate cardiac issues."},
    {"id": "doc_002", "title": "Headache", "content": "Severe headache can indicate meningitis."},
    {"id": "doc_003", "title": "Fever", "content": "Fever with rigors may indicate sepsis."},
]


def _make_tool(tmp_path: Path) -> KnowledgeBaseTool:
    corpus_file = tmp_path / "corpus.json"
    corpus_file.write_text(json.dumps(_SAMPLE_CORPUS))
    with patch("agent.tools.knowledge_base.SentenceTransformer") as mock_st:
        dim = 4
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(len(_SAMPLE_CORPUS), dim).astype(np.float32)
        mock_st.return_value = mock_model
        tool = KnowledgeBaseTool(corpus_path=corpus_file, top_k=2)
        # Replace encode for query calls with consistent single-vector output
        mock_model.encode.return_value = np.random.rand(1, dim).astype(np.float32)
    return tool


def test_tool_properties(tmp_path: Path):
    tool = _make_tool(tmp_path)
    assert tool.name == "knowledge_base"
    assert "query" in tool.input_schema["properties"]
    assert tool.input_schema["required"] == ["query"]


async def test_execute_returns_results(tmp_path: Path):
    tool = _make_tool(tmp_path)
    result = await tool.execute(query="chest pain cardiac")
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) <= 2
    for doc in result["results"]:
        assert "id" in doc
        assert "title" in doc
        assert "content" in doc


async def test_execute_empty_query_returns_empty(tmp_path: Path):
    tool = _make_tool(tmp_path)
    result = await tool.execute(query="")
    assert result == {"results": []}


async def test_execute_whitespace_query_returns_empty(tmp_path: Path):
    tool = _make_tool(tmp_path)
    result = await tool.execute(query="   ")
    assert result == {"results": []}


async def test_execute_missing_query_returns_empty(tmp_path: Path):
    tool = _make_tool(tmp_path)
    result = await tool.execute()
    assert result == {"results": []}


async def test_execute_top_k_override(tmp_path: Path):
    tool = _make_tool(tmp_path)
    result = await tool.execute(query="fever", top_k=1)
    assert len(result["results"]) <= 1


async def test_execute_returns_error_on_index_failure(tmp_path: Path):
    tool = _make_tool(tmp_path)
    tool._index = MagicMock()
    tool._index.search.side_effect = RuntimeError("index error")
    result = await tool.execute(query="something")
    assert "error" in result
    assert "index error" in result["error"]


def test_corpus_not_found_raises():
    with pytest.raises(FileNotFoundError):
        with patch("agent.tools.knowledge_base.SentenceTransformer"):
            KnowledgeBaseTool(corpus_path=Path("/nonexistent/corpus.json"))


def test_to_openai_schema(tmp_path: Path):
    tool = _make_tool(tmp_path)
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "knowledge_base"

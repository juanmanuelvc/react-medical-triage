from unittest.mock import MagicMock

import pytest

import agent.tools.symptom_ner as ner_module
from agent.tools.symptom_ner import SymptomNERTool


@pytest.fixture(autouse=True)
def reset_nlp_cache():
    original = ner_module._nlp
    yield
    ner_module._nlp = original


def _make_mock_nlp(entities: list[tuple[str, str]]) -> MagicMock:
    mock_doc = MagicMock()
    mock_doc.ents = [MagicMock(text=text, label_=label) for text, label in entities]
    return MagicMock(return_value=mock_doc)


async def test_execute_returns_diseases_and_chemicals():
    ner_module._nlp = _make_mock_nlp(
        [("chest pain", "DISEASE"), ("aspirin", "CHEMICAL"), ("headache", "DISEASE")]
    )
    tool = SymptomNERTool()
    result = await tool.execute(text="I have chest pain and headache, took aspirin")
    assert result["diseases"] == ["chest pain", "headache"]
    assert result["chemicals"] == ["aspirin"]
    assert len(result["raw_entities"]) == 3


async def test_execute_empty_text_returns_empty_lists():
    tool = SymptomNERTool()
    result = await tool.execute(text="")
    assert result == {"diseases": [], "chemicals": [], "raw_entities": []}


async def test_execute_whitespace_only_returns_empty_lists():
    tool = SymptomNERTool()
    result = await tool.execute(text="   ")
    assert result == {"diseases": [], "chemicals": [], "raw_entities": []}


async def test_execute_no_entities():
    ner_module._nlp = _make_mock_nlp([])
    tool = SymptomNERTool()
    result = await tool.execute(text="I feel unwell")
    assert result == {"diseases": [], "chemicals": [], "raw_entities": []}


async def test_execute_missing_text_kwarg_returns_empty_lists():
    ner_module._nlp = _make_mock_nlp([])
    tool = SymptomNERTool()
    result = await tool.execute()
    assert result == {"diseases": [], "chemicals": [], "raw_entities": []}


async def test_execute_returns_error_on_exception():
    ner_module._nlp = MagicMock(side_effect=RuntimeError("model failed"))
    tool = SymptomNERTool()
    result = await tool.execute(text="some text")
    assert "error" in result
    assert "model failed" in result["error"]


def test_to_openai_schema():
    tool = SymptomNERTool()
    schema = tool.to_openai_schema()
    assert schema["function"]["name"] == "symptom_ner"
    assert "text" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["text"]

import pytest

from agent.tools.base import Tool


class _ConcreteTool(Tool):
    @property
    def name(self) -> str:
        return "test_tool"

    @property
    def description(self) -> str:
        return "A tool for testing."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> dict:
        return {"result": kwargs.get("query", "")}


class _ErrorTool(Tool):
    @property
    def name(self) -> str:
        return "error_tool"

    @property
    def description(self) -> str:
        return "A tool that always fails."

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> dict:
        try:
            raise RuntimeError("something went wrong")
        except Exception as exc:
            return {"error": str(exc)}


def test_tool_is_abstract():
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]


def test_abstract_subclass_missing_name_raises():
    class _Incomplete(Tool):
        @property
        def description(self) -> str:
            return "desc"

        @property
        def input_schema(self) -> dict:
            return {}

        async def execute(self, **kwargs) -> dict:
            return {}

    with pytest.raises(TypeError):
        _Incomplete()  # type: ignore[abstract]


def test_concrete_tool_instantiates():
    tool = _ConcreteTool()
    assert tool.name == "test_tool"
    assert tool.description == "A tool for testing."
    assert "query" in tool.input_schema["properties"]


async def test_execute_returns_dict():
    tool = _ConcreteTool()
    result = await tool.execute(query="headache")
    assert result == {"result": "headache"}


def test_to_openai_schema_shape():
    tool = _ConcreteTool()
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_tool"
    assert schema["function"]["description"] == "A tool for testing."
    assert schema["function"]["parameters"] == tool.input_schema


async def test_error_tool_returns_error_dict():
    tool = _ErrorTool()
    result = await tool.execute()
    assert "error" in result
    assert result["error"] == "something went wrong"

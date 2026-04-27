from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base class for all ReAct tools.

    Subclasses must implement ``name``, ``description``, ``input_schema``, and ``execute``.
    ``execute`` must catch all exceptions and return ``{"error": "<msg>"}`` — never raise.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Run the tool and return a result dict.

        Must catch all exceptions internally and return ``{"error": "<msg>"}`` on failure.
        """
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Serialise the tool as an OpenAI-compatible function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

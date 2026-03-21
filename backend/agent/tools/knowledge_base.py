import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from agent.tools.base import Tool

_DEFAULT_CORPUS_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "evals"
    / "datasets"
    / "synthetic_medical_corpus.json"
)
_MODEL_NAME = "all-MiniLM-L6-v2"
_DEFAULT_TOP_K = 3


class KnowledgeBaseTool(Tool):
    def __init__(
        self,
        corpus_path: Path = _DEFAULT_CORPUS_PATH,
        model_name: str = _MODEL_NAME,
        top_k: int = _DEFAULT_TOP_K,
    ) -> None:
        self._top_k = top_k
        self._documents: list[dict[str, str]] = self._load_corpus(corpus_path)
        self._model = SentenceTransformer(model_name)
        self._index = self._build_index()

    @property
    def name(self) -> str:
        return "knowledge_base"

    @property
    def description(self) -> str:
        return (
            "Search a medical knowledge base for relevant clinical information "
            "using semantic similarity. Returns the top matching documents."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Clinical question or symptom description to search for.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 3).",
                },
            },
            "required": ["query"],
        }

    def _load_corpus(self, path: Path) -> list[dict[str, str]]:
        with path.open() as f:
            return json.load(f)

    def _build_index(self) -> Any:
        texts = [f"{doc['title']}. {doc['content']}" for doc in self._documents]
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        embeddings = np.array(embeddings, dtype=np.float32)
        index: Any = faiss.IndexFlatL2(embeddings.shape[1])  # pyright: ignore[reportCallIssue]
        index.add(embeddings)
        return index

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        try:
            query: str = kwargs.get("query", "")
            if not query.strip():
                return {"results": []}
            top_k: int = int(kwargs.get("top_k", self._top_k))
            top_k = min(top_k, len(self._documents))
            query_embedding = self._model.encode([query], convert_to_numpy=True)
            query_embedding = np.array(query_embedding, dtype=np.float32)
            _, indices = self._index.search(query_embedding, top_k)  # type: ignore[call-arg]
            results = [
                {
                    "id": self._documents[i]["id"],
                    "title": self._documents[i]["title"],
                    "content": self._documents[i]["content"],
                }
                for i in indices[0]
                if i < len(self._documents)
            ]
            return {"results": results}
        except Exception as exc:
            return {"error": str(exc)}

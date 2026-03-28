import warnings
from typing import Any

import spacy

from agent.tools.base import Tool

_nlp: Any = None


def _get_nlp() -> Any:
    global _nlp
    if _nlp is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _nlp = spacy.load("en_ner_bc5cdr_md")
    return _nlp


class SymptomNERTool(Tool):
    @property
    def name(self) -> str:
        return "symptom_ner"

    @property
    def description(self) -> str:
        return (
            "Extract medical entities (diseases and chemicals) from patient-reported "
            "symptom text using scispaCy NER."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Free-text patient symptom description.",
                }
            },
            "required": ["text"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        try:
            text: str = kwargs.get("text", "")
            if not text.strip():
                return {"diseases": [], "chemicals": [], "raw_entities": []}
            nlp = _get_nlp()
            doc = nlp(text)
            diseases: list[str] = []
            chemicals: list[str] = []
            raw_entities: list[dict[str, str]] = []
            for ent in doc.ents:
                raw_entities.append({"text": ent.text, "label": ent.label_})
                if ent.label_ == "DISEASE":
                    diseases.append(ent.text)
                elif ent.label_ == "CHEMICAL":
                    chemicals.append(ent.text)
            return {"diseases": diseases, "chemicals": chemicals, "raw_entities": raw_entities}
        except Exception as exc:
            return {"error": str(exc)}

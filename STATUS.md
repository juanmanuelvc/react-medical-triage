# STATUS.md

## Current Phase
Phase 3 — FastAPI + Schemas + Session persistence

## Phases

- [x] Phase 1 — Project skeleton + Tool implementations
- [x] Phase 2 — ReAct loop
- [ ] Phase 3 — FastAPI + Schemas + Session persistence
- [ ] Phase 4 — OpenTelemetry + Docker Compose
- [ ] Phase 5 — Frontend
- [ ] Phase 6 — Eval suite
- [ ] Phase 7 — Kubernetes + Makefile + Docs

## Active Tasks

(none)

## Completed

- [x] Set up CLAUDE.md, STATUS.md, justfile, .gitignore
- [x] Scaffold backend/frontend structure, pyproject.toml, uv.lock (CPU-only torch)
- [x] Add synthetic medical corpus (50 docs) and triage protocols (20 entries)
- [x] Implement abstract Tool base class with OpenAI schema helper
- [x] Implement SymptomNERTool with scispaCy en_ner_bc5cdr_md
- [x] Implement KnowledgeBaseTool with sentence-transformers and FAISS
- [x] Implement TriageProtocolTool with JSON lookup by symptom and severity
- [x] Assemble TOOL_REGISTRY from all tool instances
- [x] Unit tests for all tools (34 tests passing)
- [x] Switch branch model to trunk-based development
- [x] Implement SYSTEM_PROMPT in prompts.py
- [x] Implement ReActStep, TriageResult dataclasses and run_triage() in react_loop.py
- [x] Unit tests for react loop (7 tests, all mocked)

## Blockers

(none)

## Notes

- Legend: [ ] pending · [~] in progress · [x] done
- See PLAN.md for full file list per phase
- scispaCy model (en_ner_bc5cdr_md) not in pyproject.toml — install via uv pip install <url> after uv sync

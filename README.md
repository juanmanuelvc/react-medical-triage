# react-medical-triage

Private clinics waste triage time on patients who could be pre-oriented before seeing a nurse. This project explores using a ReAct agent to do that pre-triage automatically: the agent reasons through patient-reported symptoms, queries structured clinical tools, and returns a structured urgency recommendation — with a full reasoning trace for auditability.

Built without agent frameworks. Pure Python + LiteLLM tool calling.

---

## How it works

The agent runs a **Think → Act → Observe** cycle until it has enough information to call `finish`:

```
Patient symptom text
        │
        ▼
   ReAct Loop
        │
        ├── Think: what information is still needed?
        ├── Act:   call a tool
        │           ├── symptom_ner      extract diseases & chemicals (scispaCy)
        │           ├── knowledge_base   semantic search over clinical corpus (FAISS)
        │           └── triage_protocol  urgency lookup by symptom + severity (JSON)
        ├── Observe: incorporate result, loop
        │
        └── finish → TriageResult
                      ├── urgency_level  (immediate | urgent | semi_urgent | non_urgent)
                      ├── recommendation
                      ├── confidence     (0.0 – 1.0)
                      ├── red_flags
                      └── reasoning_summary
```

If the agent does not call `finish` within `MAX_STEPS = 10`, it escalates to `immediate` — safety over efficiency.

---

## Design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agent pattern | ReAct, no framework | Full loop control; easy to instrument; transparent reasoning trace |
| LLM routing | LiteLLM | Switch between vLLM, Anthropic, Vertex AI without touching code |
| Medical NER | scispaCy `en_ner_bc5cdr_md` | Deterministic entity extraction; offloads the LLM from parsing raw symptom text |
| Knowledge base | sentence-transformers + FAISS | Semantic search over clinical vignettes; lightweight; CPU-friendly |
| Protocol lookup | Static JSON | Triage protocols are rule-based; no computation needed |
| Corpus | Synthetic (50 docs) | No download dependency; covers common triage scenarios; easy to extend |
| Session storage | SQLite + aiosqlite | Zero-infrastructure persistence for session replay |
| Observability | OpenTelemetry → Jaeger | One span per ReAct step; full trace of the reasoning chain |

---

## Stack

| Layer | Technology |
|---|---|
| Agent loop | Pure Python — `asyncio`, `dataclasses` |
| LLM routing | LiteLLM (`acompletion`) |
| Local LLM | vLLM — Qwen2.5-0.5B-Instruct (CPU) |
| Medical NER | scispaCy `en_ner_bc5cdr_md` |
| Knowledge base | `sentence-transformers/all-MiniLM-L6-v2` + FAISS |
| Config | pydantic-settings |
| Dependency mgmt | `uv` (backend) · `npm` (frontend) |
| Task runner | `just` |

---

## Quick start

**Prerequisites:** Python ≥ 3.11 · [`uv`](https://docs.astral.sh/uv/) · [`just`](https://just.systems/)

```bash
git clone https://github.com/juanmanuelvc/react-medical-triage
cd react-medical-triage
cp .env.example .env
cd backend && uv sync
```

scispaCy's `en_ner_bc5cdr_md` model is not on PyPI — install it separately after `uv sync`:

```bash
# Find the latest release at https://github.com/allenai/scispacy/releases
uv pip install <en_ner_bc5cdr_md wheel URL>
```

**Run tests** (no LLM required — all mocked):

```bash
just test-back
```

**Lint:**

```bash
just lint-back   # ruff + pyright
```

---

## LLM provider

Switch providers by editing `.env` — no code changes needed.

```bash
# Local vLLM (default — CPU, Qwen2.5-0.5B-Instruct)
LLM_MODEL=openai/qwen2.5-0.5B-Instruct
LLM_API_BASE=http://localhost:8080/v1
LLM_API_KEY=

# Anthropic
LLM_MODEL=anthropic/claude-sonnet-4-6
LLM_API_BASE=
LLM_API_KEY=sk-ant-...

# Vertex AI
LLM_MODEL=vertex_ai/gemini-1.5-pro
LLM_API_BASE=
LLM_API_KEY=your-google-key
```

---

> This project is a software engineering exercise — not a medical device. Do not use it for real clinical decisions.

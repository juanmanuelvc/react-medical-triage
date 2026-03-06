# Implementation Plan: react-medical-triage

## Dependency management

Backend uses **`uv`** (not pip, not poetry):
- `pyproject.toml` declares all dependencies
- `uv sync` installs the virtualenv; `uv add <pkg>` adds new packages
- Docker image uses `uv` to install deps: `RUN uv sync --frozen`
- Makefile targets call `uv run pytest`, `uv run uvicorn`, etc.
- `uv.lock` is committed to the repo for reproducible installs

---

## Resolved Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| scispaCy model | Keep `en_ner_bc5cdr_md` as-is | Adapt tool output to what it actually extracts (diseases + chemicals); LLM infers severity/location in its reasoning |
| Medical KB corpus | Synthetic ~50 documents | No download dependency; realistic triage scenarios; easy to inspect and extend |
| vLLM model | `Qwen2.5-0.5B-Instruct` (CPU, INT4 quantized) | Sub-1B, runs on CPU via vLLM's CPU device support |
| Session persistence | SQLite + aiosqlite | Required — GET /triage/{id} endpoint exists |
| SSE granularity | Per ReAct step | One event per think/act/observe |
| Triage protocols | Synthetic JSON | ~20 combinations across 4 urgency levels |
| Eval dataset | 25 synthetic cases | Ground-truth urgency labels |
| Prometheus/Grafana | Skip Phase 1 | Marked optional in spec |
| UI language | English | — |

---

## Phase 1 — Project skeleton + Tool implementations

**Goal:** All tools working and unit tested. No agent loop yet.

Files:
- `backend/agent/tools/base.py` — Abstract `Tool` class: `name`, `description`, `input_schema`, `async execute(**kwargs) -> dict`. Every subclass must catch all exceptions and return `{"error": "<message>"}` on failure — never raises.
- `backend/agent/tools/symptom_ner.py` — scispaCy `en_ner_bc5cdr_md`. Output adapted to what the model actually extracts: `{"diseases": [...], "chemicals": [...], "raw_entities": [...]}`
- `backend/agent/tools/knowledge_base.py` — sentence-transformers (`all-MiniLM-L6-v2`) + FAISS. Indexes `evals/datasets/synthetic_medical_corpus.json` at startup. Returns top-k semantic matches.
- `backend/agent/tools/triage_protocol.py` — static JSON lookup by `primary_symptom` + `severity`. Returns `urgency_level`, `referral_type`, `protocol_name`, `rationale`.
- `backend/agent/tools/__init__.py` — `TOOL_REGISTRY: dict[str, Tool]`
- `evals/datasets/synthetic_medical_corpus.json` — ~50 medical QA documents covering common triage scenarios
- `infra/protocols/triage_protocols.json` — protocol lookup table (~20 entries)
- `backend/pyproject.toml` — managed by `uv` (replaces `requirements.txt`)
- `backend/tests/test_tools.py`

---

## Phase 2 — ReAct loop

**Goal:** Core agent loop end-to-end, CLI-testable, no HTTP yet.

Files:
- `backend/agent/prompts.py` — System prompt: role (medical pre-triage assistant), ReAct process description, tool list with descriptions, constraints (no diagnosis, only orient; escalate if uncertain)
- `backend/agent/react_loop.py`:
  ```python
  async def run_triage(symptoms_text: str, session_id: str) -> TriageResult:
      messages = [system_prompt, user_message(symptoms_text)]
      steps: list[ReActStep] = []
      for step_num in range(MAX_STEPS):  # default: 10
          response = await litellm.acompletion(
              model=LLM_MODEL, messages=messages,
              tools=tool_schemas, tool_choice="auto"
          )
          if tool_call == "finish": break
          result = await TOOL_REGISTRY[tool_name].execute(**tool_args)
          messages.append(assistant_msg + tool_result_msg)
          steps.append(ReActStep(...))
      return TriageResult(session_id, steps, recommendation, urgency, confidence)
  ```
- No framework imports. Pure Python + LiteLLM tool calling (OpenAI function-calling spec).
- Stop conditions: `finish` tool called, `MAX_STEPS` exceeded, agent explicitly signals escalation.
- `backend/tests/test_react_loop.py` — mock `litellm.acompletion`, verify step sequencing and all stop conditions.

---

## Phase 3 — FastAPI + Schemas + Session persistence

**Goal:** HTTP API with SSE streaming and SQLite session storage.

Files:
- `backend/api/schemas.py` — Pydantic v2:
  - `TriageRequest(symptoms: str)`
  - `ReActStepSchema(step_number, step_type, tool_name, tool_args, tool_result, reasoning, tokens_prompt, tokens_completion, latency_ms)`
  - `TriageResponse(session_id, steps, recommendation, urgency_level, confidence, red_flags, reasoning_summary)`
- `backend/api/routes/triage.py`:
  - `POST /triage` — creates `session_id`, runs `run_triage()`, streams each step as SSE `data: {json}\n\n`, final event contains full result
  - `GET /triage/{session_id}` — fetches stored session from SQLite
- `backend/api/main.py` — FastAPI app, CORS, lifespan (DB init on startup)
- SQLite schema: `triage_sessions(id TEXT PK, created_at TEXT, steps_json TEXT, result_json TEXT, status TEXT)`

---

## Phase 4 — OpenTelemetry + Docker Compose

**Goal:** Every ReAct step = one OTel span visible in Jaeger. Full local environment with `docker compose up`.

Files:
- `backend/tracing/otel.py`:
  - `setup_tracing()` — configures OTel SDK with OTLP exporter → Jaeger
  - LiteLLM callback hook to record `llm.model`, `llm.tokens_prompt`, `llm.tokens_completion`, `llm.latency_ms` per call
- Instrumentation in `react_loop.py`: each step wrapped in `tracer.start_as_current_span(f"react.step.{step_type}", attributes={...})`
  - Span attributes: `react.step_type`, `react.step_number`, `react.tool_name`, `llm.model`, `llm.tokens_prompt`, `llm.tokens_completion`, `llm.latency_ms`
- `infra/docker-compose.yml`:
  ```
  backend   → FastAPI (uvicorn), port 8000
  frontend  → Vite dev server, port 5173
  vllm      → Qwen2.5-0.5B-Instruct, CPU/INT4, port 8080
  jaeger    → jaegertracing/all-in-one, UI port 16686, OTLP gRPC port 4317
  ```
- `.env.example` — `LLM_MODEL`, `LLM_API_BASE`, `LLM_API_KEY` (defaults to local vLLM)

---

## Phase 5 — Frontend

**Goal:** Minimal React UI that streams and renders the ReAct chain-of-thought in real time.

Files:
- `frontend/src/api.js` — `startTriage(text)` opens SSE connection via `fetch` + `ReadableStream`
- `frontend/src/components/SymptomInput.jsx` — textarea + submit button
- `frontend/src/components/ReActTrace.jsx` — renders steps as they arrive: step-type badge (think/act/observe), reasoning text, collapsible tool call/result
- `frontend/src/components/Recommendation.jsx` — final urgency level (color-coded), confidence bar, red flags list
- `frontend/src/App.jsx` — composes the three components, manages SSE lifecycle
- `frontend/package.json` — Vite + React, Tailwind CSS. No component frameworks.

---

## Phase 6 — Eval suite

**Goal:** `make eval` runs automated evaluation and outputs a JSON + Markdown report.

Files:
- `evals/datasets/triage_cases.json` — 25 synthetic cases: `{id, symptoms_text, expected_urgency, notes}`. Covers all 4 urgency levels; includes edge cases (chest pain, pediatric, chronic vs acute onset).
- `evals/eval_runner.py`:
  - Iterates over cases, calls agent (real LLM, not mocked)
  - **Deterministic metrics**: steps to convergence, tool call success rate, confidence score distribution
  - **LLM-as-Judge**: sends `(symptoms, full chain-of-thought, recommendation)` to LLM; asks "Is the reasoning coherent with the conclusion? Rate 1–5 and explain."
  - Outputs `evals/results/report_{timestamp}.json` + `evals/results/report_{timestamp}.md`
- `evals/results/.gitkeep`

---

## Phase 7 — Kubernetes + Makefile + Docs

**Goal:** Production-ready infra scaffolding, full Makefile, architecture docs, README.

Files:
- `infra/k8s/backend-deployment.yaml` — 2 replicas, readiness probe on `/health`
- `infra/k8s/backend-service.yaml` — ClusterIP
- `infra/k8s/configmap.yaml` — `LLM_MODEL`, `LLM_API_BASE`, `JAEGER_ENDPOINT`
- `Makefile` targets: `dev`, `test`, `eval`, `build`, `k8s-apply`
- `docs/architecture.md` — ASCII diagram: Patient → Frontend → FastAPI → ReAct Loop → Tools → LiteLLM → vLLM/Cloud LLM
- `docs/design-decisions.md` — ReAct vs simple chain, scispaCy vs LLM for NER, tool calling vs text parsing, trade-offs
- `README.md` — per spec: What this is, Pattern, Architecture, Design decisions, Stack table, Run locally, Switch LLM provider, Eval results

---

## Critical File Map

| File | Role |
|------|------|
| `backend/agent/react_loop.py` | Core — the ReAct implementation |
| `backend/agent/tools/base.py` | Contract all tools must satisfy |
| `backend/agent/prompts.py` | LLM behavior definition |
| `backend/tracing/otel.py` | OTel instrumentation |
| `backend/api/routes/triage.py` | SSE streaming endpoint |
| `infra/docker-compose.yml` | Local dev environment |

---

## Verification

- `pytest backend/tests/` — tool unit tests + ReAct loop unit tests (mocked LLM)
- `make dev` → `docker compose up` → `POST /triage` with sample symptoms → verify SSE stream
- Jaeger UI at `localhost:16686` → find trace → verify one span per ReAct step with correct attributes
- `make eval` → verify JSON + Markdown report in `evals/results/`

[//]: # (template-version: v0.3.0)
# CLAUDE.md — react-medical-triage

Medical pre-triage assistant for private clinics using a ReAct agent loop (no agent frameworks).
See `PLAN.md` for the phase-by-phase implementation plan. See `STATUS.md` for current progress.

**Stack:** FastAPI · LiteLLM · scispaCy · sentence-transformers · FAISS · SQLite · OpenTelemetry · Jaeger · React/Vite · Tailwind · Docker Compose · Kubernetes

---

## Dependency Management

- **Backend:** `uv` only — never `pip install` or `poetry`. Lock file `uv.lock` is always committed.
  - `uv add <pkg>` · `uv sync` · `uv run <cmd>`
- **Frontend:** `npm` inside `frontend/`

---

## Task Runner

`just` (not `make`). Recipes in `justfile` at repo root.

```
just dev           # docker compose up
just test          # backend + frontend tests
just test-back     # uv run pytest backend/tests/
just test-front    # npm run test (frontend/)
just lint          # all linters
just lint-back     # ruff check + ruff format --check + pyright
just lint-front    # prettier --check + eslint
just eval          # eval suite
just build         # docker compose build
just k8s-apply     # kubectl apply -f infra/k8s/
```

---

## Git Workflow

**Branch model (git flow):**
- `main` — protected, production-ready only
- `development` — protected, integration branch
- `feat/<scope>/<slug>` — feature branches from `development`
- `feat/<scope>/<slug>/<subtask>` — sub-branches for parallel work

Never commit directly to `main` or `development`. Use `/worktree-start` to create branches and worktrees.

**Conventional Commits:** `<type>(<scope>): <description>`

Types: `feat` · `fix` · `test` · `refactor` · `docs` · `chore` · `ci`

Scopes: `tools` · `react-loop` · `api` · `tracing` · `frontend` · `infra` · `eval` · `docs` · `config`

Example: `feat(tools): add symptom NER tool using scispaCy`

**Commit discipline:**
- Complete all development work before creating any commit.
- Commits are atomic by logical unit, following SDD+TDD order: spec → test → impl.
- Commit messages are single-line, max 72 characters. No body, no co-author lines.
- Stage files by name — never `git add -A` or `git add .`.
- Review `git diff --staged` before committing.
- Never commit `.env` or credentials.
- Never push — the user reviews and pushes manually.
- After every commit sequence, `/worktree-finish` prints a summary table automatically.

---

## Development Workflow

Every task follows SDD+TDD: **spec → tests → implement → refactor → quality gates → commit.**
Run `/sdd-cycle` for the full procedure.

---

## Quality Gates

All must pass before committing. Use `just lint-back` / `just test-back` / `just lint-front` / `just test-front`.
Fix all errors — never skip or suppress checks.

---

## Worktree Workflow

Worktrees live in `.worktrees/` (gitignored). Use `/worktree-start` to enter and `/worktree-finish` to exit.

Rules:
- Do not commit until ALL parallel agents have finished development.
- Never push — the user pushes after review.
- `/worktree-finish` runs quality gates, commits, merges (if sub-branch), removes the worktree, and prints the commit summary.

For parallel sub-tasks (up to 5 agents), run `/delegate`.

---

## STATUS.md Contract

Update at every state change: `[ ]` pending · `[~]` in progress · `[x]` done.
Add blockers to the Blockers section. Keep under 50 lines. No prose — structured entries only.

---

## LLM Configuration

LiteLLM is the only permitted library for LLM calls (`litellm.acompletion()` — no wrappers).
Configuration via environment variables — switch provider without touching code:

| Variable | Local (vLLM) | Anthropic | Vertex AI |
|---|---|---|---|
| `LLM_MODEL` | `openai/qwen2.5-0.5B-Instruct` | `anthropic/claude-sonnet-4-6` | `vertex_ai/gemini-1.5-pro` |
| `LLM_API_BASE` | `http://localhost:8080/v1` | _(empty)_ | _(empty)_ |
| `LLM_API_KEY` | _(empty)_ | your key | your key |

---

## Code Style

- Explicit over clever. Descriptive names; no abbreviations.
- Types/annotations required on all public backend functions.
- Write tests before or alongside new logic.
- No comments unless logic is non-obvious.
- Minimum necessary complexity — three similar lines beats a premature abstraction.
- No error handling for impossible cases; no features beyond what is requested.
- No backwards-compatibility shims for code known to be unused.

---

## Project Constraints

- Every tool subclass must catch all exceptions and return `{"error": "<msg>"}` — never raise.
- `react_loop.py` must not import any agent framework — pure Python + LiteLLM only.
- Every `litellm.acompletion()` call must be inside an OTel span.
- Read files before modifying them. Prefer editing over creating new files.

---

## Agent Behaviour

- Ask before large, destructive, or irreversible changes.
- Use `ultrathink` for complex tasks or when self-reviewing changes.
- When context reaches ~60%, warn and suggest `/handoff` before continuing.
- Prefer concise, direct explanations — skip filler phrases.
- On errors: show root cause before proposing a fix.
- Never skip hooks (`--no-verify`) or force-push without explicit permission.
- When all tasks for a branch are complete, remind the user about `/pr-preview`.

---

## Security

- Never commit secrets, credentials, `.env` files, or tokens.
- Validate at system boundaries (user input, external APIs); trust internal guarantees.
- Do not introduce command injection, XSS, SQL injection, or other OWASP top-10 issues.

---

## Observability

Each ReAct step = one OTel span. Required span attributes:
`react.step_type` · `react.step_number` · `react.tool_name` · `llm.model` · `llm.tokens_prompt` · `llm.tokens_completion` · `llm.latency_ms`

Full session trace must be navigable in Jaeger at `localhost:16686`.

---

## Available Skills

<!-- Scan this list at the start of any non-trivial task and load relevant skills before acting. -->

| Skill | When to load |
|---|---|
| `.claude/commands/sdd-cycle.md` | spec → test → implement → refactor → quality gates → commit |
| `.claude/commands/worktree-start.md` | create branch + worktree |
| `.claude/commands/worktree-finish.md` | quality gates, commit, merge, cleanup |
| `.claude/commands/delegate.md` | parallel sub-tasks (up to 5 agents) |
| `~/.claude/skills/git-workflow/SKILL.md` | Any git operation: branch, PR, merge, rebase, conflict |
| `~/.claude/skills/quality-gates/SKILL.md` | Before committing or opening a PR — runs tests, linter, type-checker |
| `~/.claude/skills/tdd/SKILL.md` | Writing new logic, fixing bugs, adding or modifying tests |
| `~/.claude/skills/open-pr/SKILL.md` | Only when the user explicitly asks to open a PR — never proactively |
| `~/.claude/skills/versioning/SKILL.md` | Bumping versions, generating changelogs with git-cliff, tagging releases |
| `~/.claude/skills/context-mgmt/SKILL.md` | Context bar ~60%, before `/compact` or `/clear`, delegating to sub-agents |

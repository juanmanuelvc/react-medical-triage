# CLAUDE.md — react-medical-triage

Medical pre-triage assistant using a ReAct agent loop.
See `PLAN.md` for the phase-by-phase plan. See `STATUS.md` for current progress.

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

## Project Constraints

- Read files before modifying them.
- Prefer editing existing files over creating new ones.
- No comments unless logic is non-obvious.
- No error handling for impossible cases.
- No features beyond what is explicitly requested.
- Backend public functions require type hints.
- Every tool subclass must catch all exceptions and return `{"error": "<msg>"}` — never raise.

# Workflow Design Session Summary

## Context

Initial setup session for `react-medical-triage` — a medical pre-triage ReAct agent.
Goal: establish CLAUDE.md, git workflow, and agentic development conventions before implementation begins.

---

## Decisions Made

### Git Workflow
- **Git flow:** `main` (protected) · `development` (protected) · `feat/<scope>/<slug>` branches
- **Branch naming:** auto-derived by the agent from the task description — never prompted to the user
  - Pattern: `feat/<scope>/<slug>` or `feat/<scope>/<parent>/<subtask>` for parallel sub-tasks
  - Scope matches Conventional Commits scope: `tools`, `react-loop`, `api`, `tracing`, `frontend`, `infra`, `eval`, `docs`, `config`
- **Conventional Commits:** `<type>(<scope>): <description>` — types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `ci`
- **Commit discipline:** all development work first, commits last; atomic by logical unit; no `git add -A`; no push (user does that)
- **Commit summary table** printed after every commit sequence (hash, message, files, rationale)

### Task Runner
- **`just`** over `make` — cleaner syntax, no tab issues, parameterised recipes, `just --list` docs
- Recipes defined: `dev`, `test`, `test-back`, `test-front`, `lint`, `lint-back`, `lint-front`, `eval`, `build`, `k8s-apply`

### Tooling
- **Backend:** Python with `uv` exclusively (no pip, no poetry). `uv.lock` committed.
- **Linting/types:** `ruff` (check + format) + `pyright`
- **Frontend:** `npm` · Prettier · ESLint

### Worktree Workflow
- Worktrees stored in `.worktrees/` (gitignored)
- Two skills encapsulate the full lifecycle:
  - `/worktree-start <task description>` — safety check → sync development → create branch → set upstream → create worktree → print confirmation
  - `/worktree-finish <path> [--parent-branch]` — quality gates → atomic commits → merge (if sub-branch) → worktree cleanup → commit summary
- Feature branch = worktree branch directly; no separate merge step for single-agent work
- Sub-branches (`feat/x/subtask-a`) used when multiple agents work on the same feature in parallel; merged sequentially into the parent feature branch after all agents finish
- Remote upstream set immediately on branch creation (`git push -u origin <branch>`) with graceful skip if no remote configured

### Parallel Agent Delegation
- Up to 5 agents in parallel via isolated worktrees
- Pre-condition: sub-tasks must have no shared file dependencies
- Orchestrator waits for all agents to finish before any commit happens
- Sub-branches merged sequentially (not in parallel) to catch conflicts early
- Unified commit summary printed after all merges

### Development Methodology
- **Spec-Driven Development (SDD) + Test-Driven Development (TDD)**
- Order: spec → tests (red) → implement (green) → refactor → quality gates → commit
- Commit sequence mirrors this: `chore` (spec) → `test` → `feat` (impl) → `refactor`
- Spec is the source of truth; tests and impl conform to it

---

## Files Created

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project rules, conventions, and skill references — loaded every session |
| `STATUS.md` | Live task board — phase checklist, active tasks, blockers. Max 50 lines. |
| `.gitignore` | Covers `.worktrees/`, Python, Node, env files, eval results |
| `.claude/commands/worktree-start.md` | Skill: create branch + worktree from a task description |
| `.claude/commands/worktree-finish.md` | Skill: quality gates + commits + cleanup + summary |
| `.claude/commands/sdd-cycle.md` | Skill: full SDD+TDD procedure for a development task |
| `.claude/commands/delegate.md` | Skill: decompose + run parallel agents + unified summary |

---

## CLAUDE.md Design Principle

Established a clear separation of concerns:

| File | Contains |
|------|---------|
| `CLAUDE.md` | Rules, constraints, conventions (loaded every session — keep concise) |
| Skills (`/command`) | Step-by-step procedures (loaded on demand — can be verbose) |

Reduced CLAUDE.md from ~247 lines to ~91 lines by extracting procedural content into skills.

---

## Open / Future Iterations

- `justfile` not yet created — recipes are defined in CLAUDE.md but the file doesn't exist yet
- Git repo not yet initialized — no `development` branch, no remote
- Consider a `/phase-start` skill that: checks out development, creates the feature branch, updates STATUS.md, and prints the phase file list from PLAN.md
- Consider adding a pre-commit hook spec to enforce conventional commit format locally
- `spec` commit type (`chore` is currently used for schema definitions) — revisit if the convention feels wrong in practice

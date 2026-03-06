# worktree-start

Sets up an isolated git worktree for a feature branch, ready for agent handoff.
The branch name is derived automatically from the task description.

## Usage

```
/worktree-start <task description>
```

Example: `/worktree-start implement symptom NER tool using scispaCy`

## Branch naming rules

Derive the branch name from the task description using this pattern:
`feat/<scope>/<short-slug>`

**Scope** — pick the single best match:

| Scope | When to use |
|-------|-------------|
| `tools` | Agent tools (NER, KB, triage protocol) |
| `react-loop` | ReAct loop, prompts, LLM integration |
| `api` | FastAPI routes, schemas, middleware |
| `tracing` | OpenTelemetry, spans, LiteLLM hooks |
| `frontend` | React components, Vite config |
| `infra` | Docker Compose, Kubernetes, justfile |
| `eval` | Eval runner, datasets, reports |
| `docs` | Documentation, README, architecture |
| `config` | Project config, pyproject.toml, env |

**Slug** — lowercase, hyphens only, max 30 chars, derived from the key nouns/verbs in the task:
- "implement symptom NER tool using scispaCy" → `symptom-ner-tool`
- "add SSE streaming to POST /triage" → `triage-sse-streaming`
- "write unit tests for knowledge base tool" → `knowledge-base-tests`

**Sub-branch** (parallel sub-tasks only):
`feat/<scope>/<parent-slug>/<subtask-slug>`

Print the derived branch name and proceed without asking for confirmation.

## Steps

1. **Assert safety**
   - Run `git branch --show-current`.
   - If current branch is `main` or `development`: inform the user, then continue — the feature branch will be created from `development` regardless.

2. **Sync development**
   ```bash
   git fetch origin development
   git checkout development
   git pull --ff-only origin development
   ```
   If `git remote` returns no remotes, skip fetch/pull and warn: "No remote configured — working from local development branch."

3. **Create feature branch**
   ```bash
   git checkout -b <derived-branch-name>
   ```
   If the branch already exists locally, check it out and continue.

4. **Set upstream (if remote exists)**
   ```bash
   git push -u origin <derived-branch-name>
   ```
   If no remote, skip and note: "Upstream tracking skipped — no remote configured."

5. **Create worktree**
   ```bash
   git worktree add .worktrees/<sanitized-name> <derived-branch-name>
   ```
   `<sanitized-name>` replaces `/` with `-` (e.g., `feat/tools/symptom-ner-tool` → `feat-tools-symptom-ner-tool`).

   If the path already exists, remove it first:
   ```bash
   git worktree remove .worktrees/<sanitized-name> --force
   git worktree add .worktrees/<sanitized-name> <derived-branch-name>
   ```

6. **Confirm**
   Print:
   ```
   Worktree ready:
     Branch:  feat/<scope>/<slug>
     Path:    .worktrees/<sanitized-name>
     Remote:  origin/feat/<scope>/<slug> [tracked] OR [no remote]

   Starting SDD+TDD workflow:
     1. Define spec (schemas, interfaces, contracts)
     2. Write failing tests
     3. Implement
     4. Refactor
     5. Quality gates → worktree-finish
   ```

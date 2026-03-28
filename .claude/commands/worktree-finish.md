# worktree-finish

Runs quality gates, creates atomic commits, merges back, cleans up the worktree, and prints a commit summary for user review.

## Usage

```
/worktree-finish <worktree-path> [--parent-branch <branch>]
```

- `<worktree-path>`: path under `.worktrees/` (e.g., `.worktrees/feat-tools-ner`)
- `--parent-branch`: if this is a sub-branch, the feature branch to merge into (e.g., `feat/tools`)

## Steps

### 1. Quality gates (run inside worktree path)

Detect what changed and run only relevant gates:

**Backend** (if any `backend/` files changed):
```bash
uv run ruff check backend/
uv run ruff format --check backend/
uv run pyright backend/
uv run pytest backend/tests/ -v
```

**Frontend** (if any `frontend/` files changed):
```bash
cd frontend && npx prettier --check src/
cd frontend && npx eslint src/
cd frontend && npm run test
```

If any gate fails: fix the issue, re-run the failing gate, and continue. Do not skip.

### 2. Atomic commits

Group changed files by logical unit and commit in SDD+TDD order: spec → tests → implementation.

Rules:
- Follow the sequence: spec/schema commits first, test commits second, implementation commits last.
- One commit per logical change (schema definition, test suite, endpoint implementation).
- Stage specific files by name. Never `git add -A` or `git add .`.
- Commit message format: `<type>(<scope>): <description>` (Conventional Commits).
- Messages are single-line, max 72 characters. No body, no co-author lines.
- Do not push.

Example sequence:
```bash
# 1. Spec
git add backend/api/schemas.py
git commit -m "chore(api): define TriageRequest and TriageResponse schemas"

# 2. Tests
git add backend/tests/test_triage_route.py
git commit -m "test(api): add failing tests for POST /triage endpoint"

# 3. Implementation
git add backend/agent/tools/symptom_ner.py backend/agent/tools/__init__.py
git commit -m "feat(tools): implement symptom NER tool using scispaCy en_ner_bc5cdr_md"
```

When spec, tests, and implementation are tightly coupled (small utility, config file), a single commit is acceptable.

### 3. Merge back (sub-branch only)

If `--parent-branch` was given:
```bash
git checkout <parent-branch>
git merge --ff-only <sub-branch>
```
If fast-forward is not possible, report the conflict and stop. Do not force-merge.

### 4. Worktree cleanup

```bash
git worktree remove <worktree-path> --force
```

Verify:
```bash
git worktree list
```
Confirm the path is no longer listed.

If `--parent-branch` was given, also delete the sub-branch:
```bash
git branch -d <sub-branch>
```

### 5. Commit summary (mandatory)

Print a table of every commit created in this session:

```
Commits ready for review (not pushed):

| # | Hash    | Message                                      | Files                                      | Rationale                          |
|---|---------|----------------------------------------------|--------------------------------------------|------------------------------------|
| 1 | abc1234 | feat(tools): add symptom NER tool            | tools/symptom_ner.py, tools/__init__.py    | Core NER capability for Phase 1    |
| 2 | def5678 | test(tools): add unit tests for symptom NER  | tests/test_tools.py                        | Covers happy path + error return   |

Branch: feat/tools  →  push with: git push origin feat/tools
```

Do not push. The user reviews and pushes when satisfied.

# sdd-cycle

Runs the full Spec-Driven + Test-Driven development cycle for the current task.
Follow these steps in order. Do not skip any step.

## 1. Spec (write contracts first)

Define all interfaces before writing tests or implementation.

| Area | What to define |
|------|---------------|
| API | Pydantic schemas in `api/schemas.py` (request, response, error shapes) |
| Tools | `name`, `description`, `input_schema`, return shape in the tool class |
| Backend functions | Signatures with full type hints and docstrings on public interfaces |
| Frontend components | Props interface and the shape of data each component receives |

The spec is the source of truth. Tests and implementation must conform to it — not the other way around.

Commit when done: `chore(<scope>): define <name> schemas/interfaces`

## 2. Tests — red phase

Write tests that import from the spec and assert expected behavior.
Run them — they **must fail** before any implementation exists.

| Area | Location |
|------|----------|
| Backend | `backend/tests/test_<module>.py` |
| Frontend | `frontend/src/__tests__/<Component>.test.jsx` |

Rules:
- Tests must be deterministic.
- Mock all external I/O: LLM calls, filesystem, network, DB.
- Cover happy path, error path, and edge cases defined in the spec.

Commit when done: `test(<scope>): add failing tests for <feature>`

## 3. Implement — green phase

Write the minimum code to make all tests pass.
No extra features, no speculative abstractions, no premature generalization.

Run tests after each logical chunk to track progress:
```bash
just test-back   # or just test-front
```

Commit when done: `feat(<scope>): implement <feature>`

## 4. Refactor

With all tests green, clean up:
- Remove duplication
- Improve naming
- Simplify logic
- Ensure type hints are complete on all public functions

Run tests again after any refactor to confirm nothing broke.

If refactoring changes multiple logical areas, commit each separately:
`refactor(<scope>): <what was simplified>`

## 5. Quality gates

Run all relevant gates and fix every error before committing:

```bash
just lint-back    # ruff check + ruff format --check + pyright
just test-back    # pytest
just lint-front   # prettier --check + eslint
just test-front   # component tests
```

Only run frontend gates if frontend files were changed. Same for backend.

## 6. Commit sequence

Commit in SDD+TDD order when logically separable:

```
chore(api): define TriageRequest and TriageResponse schemas     ← spec
test(api): add failing tests for POST /triage endpoint          ← tests
feat(api): implement POST /triage with SSE streaming            ← impl
refactor(api): extract SSE formatting into helper               ← refactor (if any)
```

When spec + test + impl are tightly coupled (small utility), a single commit is fine.

All commits are created by `/worktree-finish` — do not commit mid-cycle.

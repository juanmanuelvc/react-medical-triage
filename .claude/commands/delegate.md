# delegate

Splits a development task into parallel sub-tasks and coordinates up to 5 agents using isolated worktrees.

## When to use

Use when a task has independent sub-tasks with no shared file dependencies.
Do not parallelize tasks that write to the same files — run them sequentially instead.

## Steps

### 1. Decompose

Break the task into sub-tasks. For each, confirm:
- [ ] No shared file dependencies with other sub-tasks
- [ ] Self-contained spec (schemas/interfaces it depends on already exist or will be created first)
- [ ] Clear, testable completion criteria

Maximum 5 sub-tasks in parallel.

### 2. Create worktrees

For each sub-task, run `/worktree-start <sub-task description>`.
This auto-derives a sub-branch name: `feat/<scope>/<parent-slug>/<subtask-slug>`.

Document the mapping:
```
Sub-task A: .worktrees/feat-tools-ner      → feat/tools/symptom-ner-tool
Sub-task B: .worktrees/feat-tools-kb       → feat/tools/knowledge-base
Sub-task C: .worktrees/feat-tools-protocol → feat/tools/triage-protocol
```

### 3. Delegate

Hand off each sub-task to an agent with:
- The worktree path to work in
- The task description and acceptance criteria
- Relevant existing files to read (schemas, base classes, related tests)
- Explicit list of files the agent is allowed to create or modify

Agents must not assume shared state (DB, env vars, models) is initialized by another agent.
Each agent runs `/sdd-cycle` independently inside its worktree.

### 4. Wait

Do not proceed until **all** agents have completed their development work and their quality gates pass.
Do not commit anything yet.

### 5. Finish each worktree

For each completed worktree, run `/worktree-finish <path> --parent-branch <feature-branch>`.

This will:
- Run quality gates
- Create atomic commits on the sub-branch
- Fast-forward merge into the parent feature branch
- Remove the worktree

Merge sub-branches **sequentially** (not in parallel) to catch conflicts early.
If a fast-forward merge fails, resolve the conflict before proceeding to the next sub-branch.

### 6. Print unified commit summary

After all worktrees are finished, print a single summary table of all commits across all sub-tasks:

```
Commits ready for review (not pushed):

| # | Hash    | Branch                     | Message                                       | Files                          |
|---|---------|----------------------------|-----------------------------------------------|--------------------------------|
| 1 | abc1234 | feat/tools/symptom-ner     | chore(tools): define symptom NER interface    | tools/base.py, schemas.py      |
| 2 | def5678 | feat/tools/symptom-ner     | test(tools): add failing tests for NER tool   | tests/test_tools.py            |
| 3 | ghi9012 | feat/tools/symptom-ner     | feat(tools): implement symptom NER tool       | tools/symptom_ner.py           |
| 4 | jkl3456 | feat/tools/knowledge-base  | feat(tools): implement knowledge base tool    | tools/knowledge_base.py        |
...

Parent branch: feat/tools  →  push with: git push origin feat/tools
```

The user reviews and pushes when satisfied.

# Usage patterns

Drop-in conventions for working with Claude inside a repo. Each pattern is a self-contained folder with a `template/` you copy into your project's `.claude/` and a short CLAUDE.md snippet that teaches Claude the convention.

| Pattern | What it does |
|---|---|
| [`task_loop/`](task_loop/) | TODO → pick → DONE cycle. Tracks what gets worked on. No artifact materialization. |
| [`artifacts_store/`](artifacts_store/) | Materialize every substantive output as a markdown artifact + INDEX. No task tracking. |
| [`artifacts_loop/`](artifacts_loop/) | Task loop + artifact materialization combined. |

## Picking a pattern

- Want a queue of work but outputs are code/changes only → `task_loop`
- Want durable analysis/report artifacts but no task queue → `artifacts_store`
- Want both (most common) → `artifacts_loop`

## Install

Copy the pattern's `template/.claude/` into your project, then paste the snippet from its `template/.claude/CLAUDE.md` into your project's `.claude/CLAUDE.md`.

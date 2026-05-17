# artifacts_loop

Combines [`task_loop`](../task_loop/) and [`artifacts_store`](../artifacts_store/): user appends tasks to `TODO.md`; Claude picks one, does the work, writes the output as a markdown artifact, logs in `DONE.md` and `INDEX.md`, removes the task.

Use this when you want both a queue of pending work and a durable record of what was done.

## Files installed

```
.claude/
  tasks/
    TODO.md      ← user appends pending tasks
    DONE.md      ← Claude prepends completed entries with artifact link
  artifacts/
    INDEX.md     ← Claude appends an entry per materialized artifact
    <SLUG>.md    ← one file per materialized output
```

## Install

1. Copy `template/.claude/tasks/` and `template/.claude/artifacts/` into your project's `.claude/`.
2. Paste [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into your project's `.claude/CLAUDE.md`.

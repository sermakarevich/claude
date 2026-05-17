# task_loop

A simple TODO → DONE workflow. The user appends tasks to `TODO.md`; Claude picks the top one, executes it, logs a summary in `DONE.md`, removes the task.

No artifact materialization — outputs stay in chat or in code. Use [`artifacts_store`](../artifacts_store/) if you also need persistent markdown outputs, or [`artifacts_loop`](../artifacts_loop/) for both.

## Files installed

```
.claude/
  tasks/
    TODO.md    ← user appends pending tasks
    DONE.md    ← Claude prepends completed entries
```

## Install

1. Copy `template/.claude/tasks/` into your project's `.claude/tasks/`.
2. Paste [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into your project's `.claude/CLAUDE.md`.

# artifacts_store

Materialize every substantive output as a markdown file under `.claude/artifacts/`, indexed in `INDEX.md`. Keeps a durable, navigable record of analyses, reports, and design decisions outside of chat.

No task tracking — combine with [`task_loop`](../task_loop/), or use [`artifacts_loop`](../artifacts_loop/) for both.

## Files installed

```
.claude/
  artifacts/
    INDEX.md   ← Claude appends an entry per materialized artifact
```

## Install

1. Copy `template/.claude/artifacts/` into your project's `.claude/artifacts/`.
2. Paste [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into your project's `.claude/CLAUDE.md`.

# Artifact tree loop

Tasks live in `.claude/tasks/TODO.md` / `DONE.md`. Substantive outputs are materialized as markdown leaves in a tree rooted at `.claude/artifacts/INDEX.md`.

**Before storing an artifact, read [`.claude/artifacts/MAINTAIN.md`](artifacts/MAINTAIN.md)** — it covers where to place the leaf, how to update indexes, and when to rebalance the tree.

## Files

```
.claude/
  tasks/{TODO,DONE}.md
  artifacts/
    INDEX.md          ← root node
    MAINTAIN.md       ← store/rebalance protocol (read before storing)
    L0/<SLUG>.md      ← leaves (and L1/, L2/, <branch>/ as the tree grows)
```

## Per task

1. Pick the top bullet from `TODO.md`. Do the work.
2. Materialize the result as a leaf (follow `MAINTAIN.md`).
3. Prepend to `DONE.md`: title, today's date, full leaf path, 1–3 sentence summary. Remove the task from `TODO.md`.

Outside the task loop, any non-trivial output also materializes via `MAINTAIN.md`. Trivial replies (one-liners, simple lookups) stay in chat. Never invent tasks; ask before adding to TODO.

To navigate the existing tree: open the root `INDEX.md`, follow the most relevant link, repeat.

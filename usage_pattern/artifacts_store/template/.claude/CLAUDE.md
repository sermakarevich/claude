# Artifacts store

Every substantive output (analysis, report, audit, design doc) is materialized as a markdown file in `.claude/artifacts/` and indexed in `INDEX.md`.

When you produce such an output:
1. Save it as `.claude/artifacts/<SLUG>.md` (UPPER_SNAKE_CASE slug).
2. Add a line to `.claude/artifacts/INDEX.md`: `[<title>](<SLUG>.md) — one-line description`.

Trivial outputs (one-line answers, simple lookups, code edits with no narrative) stay in chat.

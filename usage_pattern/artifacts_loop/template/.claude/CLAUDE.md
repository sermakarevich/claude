# Artifact loop

Tasks live in TODO/DONE; substantive outputs are materialized as markdown artifacts.

Files:
- `.claude/tasks/TODO.md` — pending tasks. User appends; Claude reads top-down.
- `.claude/tasks/DONE.md` — completed log, newest first.
- `.claude/artifacts/INDEX.md` — navigation table of artifacts.
- `.claude/artifacts/<SLUG>.md` — one file per materialized output.

For each task:
1. Pick the top bullet from `TODO.md`.
2. Do the work. Save the result as `.claude/artifacts/<SLUG>.md` (UPPER_SNAKE_CASE).
3. Prepend to `DONE.md`: title, today's date, artifact link, 1–3 sentence summary.
4. Add a line to `INDEX.md`: `[<title>](<SLUG>.md) — one-line description`.
5. Remove the task from `TODO.md`.

Outside the task loop, any non-trivial output also goes to `artifacts/<SLUG>.md` and `INDEX.md` (steps 2 + 4 only). Trivial replies (one-liners, simple lookups) stay in chat.

Never invent tasks; ask before adding to TODO.

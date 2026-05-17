# Task loop

Tasks live in two files:
- `.claude/tasks/TODO.md` — pending tasks. User appends; Claude reads top-down.
- `.claude/tasks/DONE.md` — completed log, newest first.

For each task:
1. Pick the top bullet from `TODO.md`.
2. Do the work.
3. Prepend to `DONE.md`: title, today's date, 1–3 sentence summary of the result.
4. Remove the task from `TODO.md`.

Never invent tasks; ask before adding to TODO.

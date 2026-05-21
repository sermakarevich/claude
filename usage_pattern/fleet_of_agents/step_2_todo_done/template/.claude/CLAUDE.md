# Task queue + per-task artifacts

Tasks come from `.claude/tasks/TODO.md` (a bullet list, top entry next). For each task you materialize on-disk artifacts under `.claude/tasks/<task_id>/`, log the result to `.claude/tasks/DONE.md`, and remove the consumed bullet from `TODO.md`. This survives across sessions: re-invoking you on the same id continues the work instead of restarting it.

## Per-task artifact directory

Each task lives at `.claude/tasks/<task_id>/` with three files:

- `TASK.md` — one-paragraph restatement of the task in your own words.
- `PLAN_AND_PROGRESS.md` — numbered checklist of steps, with status markers (see format below). Keep this current as you work.
- `FINDINGS.md` — substantive output, decisions, or discoveries surfaced while doing the work. Plain markdown. Optional — create it only when there is something worth recording.

## Resume rule (do this FIRST when given a `task_id`)

Before doing anything else, check whether `.claude/tasks/<task_id>/` already exists.

- If it does, read `TASK.md`, `PLAN_AND_PROGRESS.md`, and `FINDINGS.md` (whichever exist) before any other action.
- Continue from the first `[ ]` or `[!]` item in `PLAN_AND_PROGRESS.md`. Do not restart from scratch and do not silently overwrite prior content.
- If the directory does not exist, create it and write `TASK.md` first.

## Update rule

Keep `PLAN_AND_PROGRESS.md` current as work progresses. Tick items off (`[ ]` → `[x]`) as you finish them. Add new items if the plan grows. Append to the optional `## Notes` section for free-form running notes.

Record substantive results in `FINDINGS.md` — the answers, decisions, or discoveries that a future reader (or future you) would need. Skip it for trivial work.

## `PLAN_AND_PROGRESS.md` format

Plain markdown. A numbered list with one of four status markers per item:

- `[ ]` — todo
- `[x]` — done
- `[?]` — open question (details in `FINDINGS.md` or inline)
- `[!]` — blocker

Example:

```
# Plan & Progress — t-001

1. [x] Read existing artifacts
2. [x] Restate task in TASK.md
3. [ ] Implement parser
4. [ ] Add tests
5. [?] Should we cache results? (→ see FINDINGS.md)

## Notes
- <free-form running notes here>
```

Keep it short. One pass to read; status visible inline.

## TODO → DONE flow

When the user prompts you to take the next task (e.g. `take the next task per CLAUDE.md`):

1. Read `.claude/tasks/TODO.md`. Pick the top bullet (the first non-empty `- ` line).
2. Pick a sequential `<task_id>` — the next available `t-NNN` based on existing subdirectories in `.claude/tasks/` (e.g. if `t-001/` and `t-002/` exist, use `t-003`).
3. Do the work, materializing the three artifacts under `.claude/tasks/<task_id>/` per the rules above.
4. Prepend a dated entry to `.claude/tasks/DONE.md` with this shape:

   ```
   - **<title>** (<YYYY-MM-DD>)
     - Summary: 1–3 sentences on what was done and the result.
     - Artifacts: .claude/tasks/<task_id>/
   ```

5. Remove the consumed bullet from `.claude/tasks/TODO.md`.

## Discipline

Never invent tasks. If you think a task should be added to `TODO.md`, ask the user first.

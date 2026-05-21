# Per-task artifacts

When the user gives you a task with a `task_id` (e.g. `work on task t-001: <description>`), materialize the work as on-disk files in `.claude/tasks/<task_id>/`. This survives across sessions: re-invoking you with the same id continues the work instead of restarting it.

## Per-task artifact directory

Each task lives at `.claude/tasks/<task_id>/` with three files:

- `TASK.md` — one-paragraph restatement of the task in your own words.
- `PLAN_AND_PROGRESS.md` — numbered checklist of steps, with status markers (see format below). Keep this current as you work.
- `FINDINGS.md` — substantive output, decisions, or discoveries surfaced while doing the work. Plain markdown. Optional — create it only when there is something worth recording.

## Resume rule (do this FIRST)

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

# Beads-driven task queue + per-task artifacts

Tasks come from **beads** (`bd`), a local SQLite-backed task DB. A bash `loop.sh` peeks `bd ready`, atomically claims the next task, pre-creates an artifact directory, and invokes you with the task id. For each task you materialize on-disk artifacts under `.claude/tasks/<task_id>/` and close the task in beads when done. Multiple `loop.sh` instances can run in parallel — each has a distinct `BEADS_ACTOR`, so atomic claiming prevents collisions.

## Per-task artifact directory

Each task lives at `.claude/tasks/<task_id>/` with three files:

- `TASK.md` — one-paragraph restatement of the task in your own words.
- `PLAN_AND_PROGRESS.md` — numbered checklist of steps, with status markers (see format below). Keep this current as you work.
- `FINDINGS.md` — substantive output, decisions, or discoveries surfaced while doing the work. Plain markdown. Optional — create it only when there is something worth recording.

## Resume rule (do this FIRST)

Before doing anything else, check whether `.claude/tasks/<task_id>/` already contains files from a prior iteration (the loop pre-creates the directory, so it always exists — but it may be empty).

- If `TASK.md`, `PLAN_AND_PROGRESS.md`, or `FINDINGS.md` exists, read them all before any other action.
- Continue from the first `[ ]` or `[!]` item in `PLAN_AND_PROGRESS.md`. Do not restart from scratch and do not silently overwrite prior content.
- If no artifacts exist yet, write `TASK.md` first.

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
# Plan & Progress — bd-1

1. [x] Read existing artifacts
2. [x] Restate task in TASK.md
3. [ ] Implement parser
4. [ ] Add tests
5. [?] Should we cache results? (→ see FINDINGS.md)

## Notes
- <free-form running notes here>
```

Keep it short. One pass to read; status visible inline.

## Beads task flow

When the loop invokes you, it will have already:

- Claimed a single task for you in beads (`assignee=you`, `status=in_progress`).
- Pre-created `.claude/tasks/<task_id>/`.
- Passed the task id and artifact directory in the prompt.

Your job per invocation:

1. **Resume check first** — read existing `TASK.md`, `PLAN_AND_PROGRESS.md`, `FINDINGS.md` if present (see Resume rule above).
2. **Do NOT call `bd ready`** — the loop already picked your task. Work on the assigned id only.
3. **Read task details** — run `bd show <task_id>` if you need the full title, description, or notes.
4. **Do the work** — materialize the three artifacts under `.claude/tasks/<task_id>/` per the rules above.
5. **Close on completion** — when all `PLAN_AND_PROGRESS.md` items are `[x]`, run:

   ```bash
   bd close <task_id> --reason completed
   ```

6. **If the task is genuinely undoable** (not just unclear — that's a question, which arrives in a later step), release it:

   ```bash
   bd update <task_id> --status blocked --assignee "" --notes "<short reason>"
   ```

## Loop awareness

`loop.sh` invokes you once per claimed task and re-invokes you on the next iteration with the next ready task — the same prompt each time. Your job per invocation is exactly the Beads task flow above. The loop runs forever — when `bd ready` returns no tasks it sleeps and re-peeks; the human stops it with `Ctrl+C`. If you exit non-zero, the loop releases your claimed task back to `ready` so it can be retried.

## Discipline

Never invent tasks. If you think a task should be added to the queue, ask the user — do not call `bd create` yourself.

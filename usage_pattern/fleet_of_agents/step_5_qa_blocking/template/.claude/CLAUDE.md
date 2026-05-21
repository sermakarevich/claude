# Beads-driven task queue + per-task artifacts + Q&A blocking

Tasks come from **beads** (`bd`), a local SQLite-backed task DB. A bash `loop.sh` peeks `bd ready`, atomically claims the next task, pre-creates an artifact directory, and invokes you with the task id. For each task you materialize on-disk artifacts under `.claude/tasks/<task_id>/` and close the task in beads when done. Multiple `loop.sh` instances can run in parallel — each has a distinct `BEADS_ACTOR`, so atomic claiming prevents collisions.

When you hit an ambiguity you should not resolve alone, write the question to `Q&A.md` and block the task in beads. The loop skips blocked tasks automatically. A human answers by appending to the same file and flipping the status back to `open`; the loop re-picks the task on its next iteration and you continue from where you stopped.

## Per-task artifact directory

Each task lives at `.claude/tasks/<task_id>/` with four files:

- `TASK.md` — one-paragraph restatement of the task in your own words.
- `PLAN_AND_PROGRESS.md` — numbered checklist of steps, with status markers (see format below). Keep this current as you work.
- `FINDINGS.md` — substantive output, decisions, or discoveries surfaced while doing the work. Plain markdown. Optional — create it only when there is something worth recording.
- `Q&A.md` — append-only thread of questions you asked the human and their answers. Optional — create it only on first question.

## Resume rule (do this FIRST)

Before doing anything else, check whether `.claude/tasks/<task_id>/` already contains files from a prior iteration (the loop pre-creates the directory, so it always exists — but it may be empty).

- If `TASK.md`, `PLAN_AND_PROGRESS.md`, `FINDINGS.md`, or `Q&A.md` exists, read them all before any other action.
- If `Q&A.md` contains a `## Q:` block followed by a fresh `## A:` block you have not yet acted on, treat that as the human's answer to the prior question — continue from the `[!]` item in `PLAN_AND_PROGRESS.md` it points at, do not re-ask.
- Otherwise continue from the first `[ ]` or `[!]` item in `PLAN_AND_PROGRESS.md`. Do not restart from scratch and do not silently overwrite prior content.
- If no artifacts exist yet, write `TASK.md` first.

## Update rule

Keep `PLAN_AND_PROGRESS.md` current as work progresses. Tick items off (`[ ]` → `[x]`) as you finish them. Add new items if the plan grows. Append to the optional `## Notes` section for free-form running notes.

Record substantive results in `FINDINGS.md` — the answers, decisions, or discoveries that a future reader (or future you) would need. Skip it for trivial work.

## `PLAN_AND_PROGRESS.md` format

Plain markdown. A numbered list with one of four status markers per item:

- `[ ]` — todo
- `[x]` — done
- `[?]` — open question (details in `FINDINGS.md` or inline)
- `[!]` — blocker (use this when you have asked a question in `Q&A.md` and are about to mark the task `blocked` in beads)

Example:

```
# Plan & Progress — bd-1

1. [x] Read existing artifacts
2. [x] Restate task in TASK.md
3. [!] Implement parser  → see Q&A.md
4. [ ] Add tests
5. [?] Should we cache results? (→ see FINDINGS.md)

## Notes
- <free-form running notes here>
- 2026-05-21: blocked on item 3, awaiting answer in Q&A.md
```

Keep it short. One pass to read; status visible inline.

## Beads task flow

When the loop invokes you, it will have already:

- Claimed a single task for you in beads (`assignee=you`, `status=in_progress`).
- Pre-created `.claude/tasks/<task_id>/`.
- Passed the task id and artifact directory in the prompt.

Your job per invocation:

1. **Resume check first** — read existing `TASK.md`, `PLAN_AND_PROGRESS.md`, `FINDINGS.md`, `Q&A.md` if present (see Resume rule above).
2. **Do NOT call `bd ready`** — the loop already picked your task. Work on the assigned id only.
3. **Read task details** — run `bd show <task_id>` if you need the full title, description, or notes.
4. **Do the work** — materialize artifacts under `.claude/tasks/<task_id>/` per the rules above.
5. **Close on completion** — when all `PLAN_AND_PROGRESS.md` items are `[x]`, run:

   ```bash
   bd close <task_id> --reason completed
   ```

6. **If you need a human answer** — follow the Q&A protocol below (ask, block, stop). Do NOT close. Do NOT release the assignee.
7. **If the task is genuinely undoable** (not just unclear — that's a question, see Q&A protocol), release it:

   ```bash
   bd update <task_id> --status blocked --assignee "" --notes "<short reason>"
   ```

## Loop awareness

`loop.sh` invokes you once per claimed task and re-invokes you on the next iteration with the next ready task — the same prompt each time. Your job per invocation is exactly the Beads task flow above. The loop runs forever — when `bd ready` returns no tasks it sleeps and re-peeks; the human stops it with `Ctrl+C`. If you exit non-zero, the loop releases your claimed task back to `ready` so it can be retried. Tasks you mark `blocked` are skipped by `bd ready` until a human re-opens them; the loop then re-picks them and you resume from the answer in `Q&A.md`.

## Q&A protocol (asking the human)

### When to ask

You should ask the human, not guess, when:

- A load-bearing decision affects scope, public interface, schema, or naming and the task spec is silent.
- A required input is missing (a credential, a path, an example, an acceptance threshold).
- Two reasonable approaches diverge in cost/risk and you have no rule to choose between them.

You should NOT ask when:

- The task spec contains the answer (re-read it).
- The choice is local and reversible (pick one; record in `FINDINGS.md`).
- You can verify the answer yourself (run the test, read the file, check the schema).

### How to ask

1. Append a `## Q:` block to `.claude/tasks/<task_id>/Q&A.md`. Create the file if absent. Format:

   ```markdown
   ## Q: <one-line question> — <YYYY-MM-DD HH:MM, $BEADS_ACTOR>

   **Context:** <what you were doing, with file paths / line numbers>
   **Tried:** <approaches you considered and why each falls short>
   **Need:** <what specifically you need from the human>
   ```

2. Update `PLAN_AND_PROGRESS.md`: mark the relevant item `[!]` with `→ see Q&A.md`, and add a `## Notes` line pointing at the question.

3. Mark the task blocked in beads:

   ```bash
   bd update <task_id> --status blocked
   ```

   Optionally also: `bd comment <task_id> "QUESTION — see Q&A.md"` for visibility in `bd show`. Not required.

4. Stop. Do NOT close the task. Do NOT release the assignee — keep it claimed under your `BEADS_ACTOR` so the human can see who is waiting.

### Q&A.md append-only rule

Never edit or delete prior `## Q:` or `## A:` blocks. Multiple rounds accumulate in the same file across iterations — the full history is the conversation. Each `## Q:` MUST be followed by an `## A:` from a human before you resume.

### On resume after an answer

Your resume check (above) reads `Q&A.md`. If a new `## A:` block exists below your prior `## Q:`:

- That is the human's answer. Continue from the `[!]` item in `PLAN_AND_PROGRESS.md` the question pointed at, applying the answer.
- Flip the `[!]` back to `[ ]` (about to do) or to `[x]` if the answer resolved it directly, and append a `## Notes` line recording the resolution.
- Do not re-ask. Do not restate the question in chat.

If you got re-invoked but no `## A:` exists yet (the human pushed it back to `open` without answering), restate the question briefly in `Q&A.md` (a new `## Q:` block referencing the prior one), mark the task `blocked` again, and stop.

## Discipline

Never invent tasks. If you think a task should be added to the queue, ask the user via `Q&A.md` — do not call `bd create` yourself.

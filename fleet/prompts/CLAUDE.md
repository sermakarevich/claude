# Fleet Task Protocol

You are running inside a headless fleet supervisor. The supervisor does NOT pass `--resume`; this file and the artifact directory ARE the continuation state.
Follow every section below on every invocation.

---

## On every fresh start, read these files first

Before doing anything else — before reading the task, before writing code —
run `ls "$ARTIFACT_DIR"` and read every file that exists:

- `PLAN.md` — your task restatement, steps, and assumptions from a prior run.
- `STATE.md` — progress marker: what is done, in-progress, blocked.
- `Q&A.md` — Q&A thread (see §"When blocked" below). If an `## A:` block
  exists that was not there on a prior run, the human has answered your
  question; continue from where you stopped.
- `events.jsonl` — structured events emitted by the supervisor. Useful for
  diagnosing why a prior attempt was interrupted.

The fleet does **NOT** pass `--resume`. These files are your only window into
prior attempts. If you skip this step, you will restart from scratch and waste
retries.

---

## Writing progress as you work

Keep `PLAN.md` and `STATE.md` current:

**PLAN.md** (write before any code/file changes):
- One-paragraph restatement of the task.
- Numbered steps you intend to take.
- Assumptions and open questions that, if wrong, would change the plan.

**STATE.md** (update after each substantive step):

```
# <task_id> — STATE

**Status:** in_progress | blocked | completed

## Done
- <bullet>

## In progress
- <bullet>

## Blocked
- <bullet, or "none">
```

Never delete prior content from these files — append and overwrite status only.
Task-specific outputs (`REPLY.md`, `RESULT.md`, etc.) can also live in the
artifact directory.

---

## When done

1. Update `STATE.md` with a final summary (move "In progress" to "Done").
2. Run:
   ```
   bd close <task_id> --reason "<short summary of what was done>"
   ```
3. Exit cleanly (exit code 0).

---

## When blocked by ambiguity (Q&A protocol)

When you hit an ambiguity, missing context, or a decision you should not make
alone:

1. Append a `## Q:` block to `$ARTIFACT_DIR/Q&A.md` (create the file if it
   does not exist). Shape:

   ```markdown
   ## Q: <one-line question> — <YYYY-MM-DD HH:MM, your loop actor>

   **Context:** <what you were doing, with file paths / line numbers>
   **Tried:** <approaches you considered>
   **Need:** <what specifically you need from the user>
   ```

   `Q&A.md` is **append-only** — never edit or delete prior blocks.

2. Run:
   ```
   bd update <task_id> --status blocked --notes "QUESTION: <one-line summary>"
   ```

3. Optionally add more context:
   ```
   bd comment <task_id> "<longer context visible in bd show>"
   ```

4. Update `STATE.md` Blocked with a one-liner pointer:
   `Blocked on question in Q&A.md: <one-line summary>`.

5. **Exit cleanly** (exit code 0). Do **not** close the task. Do **not**
   release the assignee.

> **Note:** The fleet does NOT provide `fleet block` or `fleet answer`
> commands. Use `bd` directly as shown above.

---

## When the human resumes you (FR-17)

The human answers by:

1. Appending an `## A:` block directly below your `## Q:` block in `Q&A.md`.
2. Running `bd update <task_id> --status open`.

The supervisor will re-claim the task on the next scheduling cycle. On that
next invocation, your resume check (§"On every fresh start") will find the
`## A:` block and you should continue from where you stopped — not restart.

---

## AskUserQuestion is not available

The `AskUserQuestion` tool is **denied** by a PreToolUse hook in headless fleet
mode. If you attempt it, the hook will block the call and emit a corrective
message.

Use the Q&A protocol above (§"When blocked") instead.

---

## Failure behavior

If you exit with a non-zero code (crash, uncaught exception, unhandled panic),
the supervisor will:

- Release the task back to the queue.
- Retry up to `retry_limit` times (default 3, configurable in
  `.fleet/runtime.toml`).

**Rate-limit interruptions and context-pressure exits do NOT count against
`retry_limit`** — the supervisor detects these and pauses/retries without
penalizing the attempt counter.

Write `STATE.md` faithfully: it is your best tool for communicating to the
next attempt what was already done, so work is not repeated.

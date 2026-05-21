# Step 5 — Q&A blocking (humans answer mid-flight)

## What this step adds

Agents can now ask the human a question instead of guessing on a load-bearing decision. The agent writes its question to a fourth per-task artifact, `Q&A.md`, and marks the task `blocked` in beads. The loop skips blocked tasks automatically. The human answers by appending to the same file and flipping the status back to `open` — the loop re-picks the task on its next iteration and Claude reads the answer on resume. No changes to `loop.sh`: the whole flow rides on `bd update --status blocked` plus a file convention in `CLAUDE.md`.

## Files installed

```
loop.sh              ← unchanged from step 4 (bd-driven loop)
.claude/
  CLAUDE.md          ← rules: per-task artifacts (now four) + beads task flow + loop awareness + Q&A protocol
  tasks/             ← per-task subdirectories, pre-created by loop.sh per claimed id
    <task_id>/
      TASK.md                ← one-paragraph restatement of the task
      PLAN_AND_PROGRESS.md   ← numbered checklist with status markers (incl. [!] for "blocked on a question")
      FINDINGS.md            ← decisions, results, discoveries (optional)
      Q&A.md                 ← append-only Q&A thread with the human (optional, created on first question)
```

`loop.sh` is byte-identical to step 4's. `.beads/` is created by `bd init` (not shipped). `logs/iter-<timestamp>.log` files are written by `loop.sh` at runtime (not shipped). `Q&A.md` is written by the agent at runtime on its first question — not shipped.

## Install

```bash
cp -r template/. .
chmod +x loop.sh
```

Install the `bd` CLI from upstream: https://github.com/gastownhall/beads. Then initialize beads in the project:

```bash
bd init
```

`jq` is also required (the loop parses `bd ready --json`).

If your project already has a `.claude/CLAUDE.md`, paste the contents of [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into the existing file instead of overwriting it.

## Try it

This walkthrough exercises the blocking → answer → resume cycle. It assumes you have completed the step 4 install (beads initialized, `loop.sh` executable, `CLAUDE.md` in place — overwritten with step 5's).

1. Create a task whose description is deliberately ambiguous so Claude has to ask:

   ```bash
   bd create -t "Generate the sample report" \
             -d "Use the right format. Save it next to the data."
   ```

2. Start the loop in one terminal:

   ```bash
   ./loop.sh
   ```

   Claude claims the task, reads the description, and (per the Q&A protocol in `CLAUDE.md`) appends a `## Q:` block to `.claude/tasks/<task_id>/Q&A.md` asking what "the right format" means and which directory counts as "next to the data". It then runs `bd update <task_id> --status blocked` and exits cleanly.

3. Observe the block in another terminal:

   ```bash
   bd list --status blocked
   # → shows the task id
   cat .claude/tasks/<task_id>/Q&A.md
   # → shows the ## Q: block with Context / Tried / Need
   ```

   The loop in terminal 1 keeps running but skips the blocked task on every iteration (`bd ready` no longer returns it).

4. Answer the question. Open `.claude/tasks/<task_id>/Q&A.md` in your editor and append an `## A:` block directly below the `## Q:`:

   ```markdown
   ## A: CSV next to inputs/ — 2026-05-21 18:00, sergii

   Use CSV. Write to `outputs/` at the project root.
   ```

5. Re-open the task in beads:

   ```bash
   bd update <task_id> --status open
   ```

6. On the next loop iteration the task is back in `bd ready`. The loop claims it and re-invokes Claude. Claude's resume check reads `Q&A.md`, sees the new `## A:` below its prior `## Q:`, flips the `[!]` item in `PLAN_AND_PROGRESS.md` back to `[ ]` (or `[x]` if the answer resolved it directly), and continues — no re-asking, no restart from scratch. When the work finishes Claude runs `bd close <task_id> --reason completed`.

7. Confirm the file history:

   ```bash
   cat .claude/tasks/<task_id>/Q&A.md
   # → still contains the original ## Q: and ## A: blocks (append-only; never edited or deleted)
   cat .claude/tasks/<task_id>/PLAN_AND_PROGRESS.md
   # → the formerly [!] item is now [x]; a Notes line records the resolution
   ```

### Q&A.md format reminder

```markdown
## Q: <one-line question> — <YYYY-MM-DD HH:MM, $BEADS_ACTOR>

**Context:** <what you were doing, with file paths / line numbers>
**Tried:** <approaches you considered>
**Need:** <what specifically you need from the human>

## A: <one-line summary> — <YYYY-MM-DD HH:MM, human>

<free-form answer text>
```

Append-only. Never edit or delete prior blocks. Multiple rounds accumulate.

### What the loop does NOT do

`loop.sh` is unchanged from step 4. It does not parse `Q&A.md`, does not check `bd list --status blocked`, and does not notify you when a task blocks. The Q&A flow is implemented entirely in `CLAUDE.md` (agent side) plus the human's out-of-band actions (answer file + `bd update --status open`). Use `tail -f logs/iter-*.log` or `bd list --status blocked` to discover pending questions.

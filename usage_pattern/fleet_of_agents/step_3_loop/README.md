# Step 3 — loop.sh

## What this step adds

Replace manually re-prompting Claude with a tiny bash loop. `./loop.sh` invokes `claude -p` once per pending task and exits when the queue is empty. Per-task artifacts and the TODO/DONE flow from prior steps are unchanged.

## Files installed

```
loop.sh                ← bash while-loop, ~15 lines
.claude/
  CLAUDE.md            ← rules: per-task artifacts + TODO/DONE flow + loop awareness
  tasks/
    TODO.md            ← pending tasks; reader appends bullets
    DONE.md            ← completed log, newest first
    <task_id>/         ← per-task subdirectories, created by Claude on demand
      TASK.md                ← one-paragraph restatement of the task
      PLAN_AND_PROGRESS.md   ← numbered checklist with status markers
      FINDINGS.md            ← decisions, results, discoveries (optional)
```

## Install

```bash
cp -r template/. .
chmod +x loop.sh
```

If your project already has a `.claude/CLAUDE.md`, paste the contents of [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into the existing file instead of overwriting it.

## Try it

1. Append three task bullets to `.claude/tasks/TODO.md`:

   ```
   - Read README.md and summarize what this project does
   - List the top-level files and group them by purpose
   - Find any TODO comments in the codebase and list them
   ```

2. Run the loop:

   ```bash
   ./loop.sh
   ```

3. Observe: one log line per iteration (`→ iter 1`, `→ iter 2`, `→ iter 3`), three iterations, then `TODO empty, stopping.`

4. Verify:

   ```bash
   cat .claude/tasks/TODO.md    # only the empty seed bullet remains
   cat .claude/tasks/DONE.md    # three new entries, newest first, each dated
   ls .claude/tasks/             # t-001/  t-002/  t-003/  TODO.md  DONE.md
   ```

5. Cap iterations with `MAX_ITERS=2 ./loop.sh` if you want to stop early; default is 100.

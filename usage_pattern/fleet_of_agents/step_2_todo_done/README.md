# Step 2 — TODO/DONE queue

## What this step adds

Replace the user's verbal "take the next task" with an on-disk queue. The reader appends bullets to `.claude/tasks/TODO.md`; the agent picks from the top, does the work, and logs each completion to `.claude/tasks/DONE.md`. Per-task artifacts from step 1 (`TASK.md`, `PLAN_AND_PROGRESS.md`, `FINDINGS.md` under `.claude/tasks/<task_id>/`) are unchanged.

## Files installed

```
.claude/
  CLAUDE.md          ← rules: per-task artifacts + TODO/DONE flow
  tasks/
    TODO.md          ← pending tasks; reader appends bullets
    DONE.md          ← completed log, newest first
    <task_id>/       ← per-task subdirectories, created by Claude on demand
      TASK.md                ← one-paragraph restatement of the task
      PLAN_AND_PROGRESS.md   ← numbered checklist with status markers
      FINDINGS.md            ← decisions, results, discoveries (optional)
```

## Install

```bash
cp -r template/.claude .claude
```

If your project already has a `.claude/CLAUDE.md`, paste the contents of [`template/.claude/CLAUDE.md`](template/.claude/CLAUDE.md) into the existing file instead of overwriting it.

## Try it

1. Append three task bullets to `.claude/tasks/TODO.md`:

   ```
   - Read README.md and summarize what this project does
   - List the top-level files and group them by purpose
   - Find any TODO comments in the codebase and list them
   ```

2. Open a Claude session in the project and prompt: `take the next task per CLAUDE.md`.
3. Verify:

   ```bash
   cat .claude/tasks/TODO.md    # shrunk by one (top bullet gone)
   cat .claude/tasks/DONE.md    # one new entry at the top, dated, with summary
   ls .claude/tasks/t-001/      # TASK.md  PLAN_AND_PROGRESS.md  FINDINGS.md
   ```

4. Prompt `take the next task per CLAUDE.md` again — Claude picks the next bullet and creates `.claude/tasks/t-002/`.

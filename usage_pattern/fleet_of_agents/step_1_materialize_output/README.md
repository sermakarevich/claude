# Step 1 — Materialize output

## What this step adds

Teach the agent to materialize task context (description, plan/progress, findings) as on-disk files in `.claude/tasks/<task_id>/`, so work survives across sessions. A reader can stop here and already get most of the value: every task leaves a paper trail, and re-invoking Claude on the same `task_id` resumes from the last unfinished step instead of restarting from scratch.

## Files installed

```
.claude/
  CLAUDE.md          ← rules: where artifacts live, resume rule, file shape
  tasks/             ← per-task subdirectories, created by Claude on demand
    <task_id>/
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

1. Open a Claude session in the project.
2. Prompt: `work on task t-001: read README.md and tell me what this project does`.
3. Verify the three files exist:

   ```bash
   ls .claude/tasks/t-001/
   # TASK.md  PLAN_AND_PROGRESS.md  FINDINGS.md
   ```

4. Re-invoke Claude with the same id (`work on task t-001: continue`) and confirm Claude reads the existing files first and continues from the first unchecked item in `PLAN_AND_PROGRESS.md` rather than restarting.

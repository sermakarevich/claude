# From one Claude agent to a fleet — in five small steps

I was intrigued by an AMD issue on GitHub where Stella Laurenzo shared how the AMD team runs a fleet of 50 or so agents: https://github.com/anthropics/claude-code/issues/42796. I wanted to get there myself, and I think I managed to. I can now run a fleet of coding agents while I'm away, burning through every token across my three Claude subscriptions. I can run data science experiments overnight in loops: analyze misclassifications, form a hypothesis, implement, run, analyze again. Agents pull tasks from a queue, add new tasks back to it, organize dependencies, and block tasks when they need my input. This article walks through my approach step by step.

---

## Step 1 — Make the agent write its work to disk

The default Claude session is a conversation. Close the window and most of the context is gone. The first move is to push the agent's replies out of the terminal and onto disk.

For every task you give the agent, it creates a folder:

```
.claude/tasks/t-001/
  TASK.md                ← one-paragraph restatement of what you asked
  PLAN_AND_PROGRESS.md   ← numbered checklist with status markers
  FINDINGS.md            ← decisions, results, things it discovered
```

This is set up with a few lines in `.claude/CLAUDE.md` — the file Claude reads at the start of every session. The rule is roughly: "When the user gives you a task with an id, create this folder if it doesn't exist; if it does exist, read the files first and continue from the first unfinished step."

What changes:

- Every task leaves a paper trail you can audit later.
- If you close the session mid-task, you can resume by re-prompting with the same id. The agent reads its own progress file and picks up where it left off — no re-explaining.
- You stop being the agent's memory.

---

## Step 2 — A queue on disk

Once tasks leave artifacts behind, the next bottleneck is **you** saying "now do this one." To write the next task you typically have to wait for the previous one to complete. Replace that with a queue.

```
.claude/tasks/TODO.md   ← you append bullets
.claude/tasks/DONE.md   ← agent prepends a summary entry when it finishes
```

The CLAUDE.md rule becomes: "Take the top line from `TODO.md`. Do the work (still writing per-task artifacts from step 1). Prepend a dated summary entry to `DONE.md`. Delete the line from `TODO.md`."

A queue lets you accumulate requests — no need to wait for task completion. The registry of finished tasks matters too: it keeps track of what you've already tried. Iterating through tasks then becomes just calling `/clear` after each one and prompting "take the next task".

---

## Step 3 — A bash loop

The next obvious move: stop typing "take the next task" yourself. Wrap it in a script.

```bash
./loop.sh
```

About fifteen lines of bash. Inside the loop it calls `claude -p "take next task from TODO.md per CLAUDE.md"` once per pending task.

Two things to notice:

1. **Nothing in the agent changed.** The CLAUDE.md rules from step 2 still do all the actual work. The loop is dumb — it just keeps re-invoking Claude.
2. **There's no wrapper around `claude`.** No abstractions, no Python framework. You can read the whole loop in one screen.

This is the first point where you can walk away and come back to a stack of completed tasks. You can also have Claude append new tasks to `TODO.md` itself when it discovers follow-up work.

---

## Step 4 — Beads, and a fleet

Now we go from "one agent in a loop" to "many agents in a loop, on the same queue, without colliding."

The problem with `TODO.md` is that two processes editing the same file race. Whoever writes last wins; tasks get lost, or worse, done twice. To go parallel you need a queue with **atomic claiming**: when one loop grabs a task, no other loop can grab it at the same instant.

I use [`beads`](https://github.com/gastownhall/beads) (the `bd` CLI) for this. It's a local SQLite-backed task DB with dependencies, statuses, and atomic updates. The shift looks like:

- `TODO.md` / `DONE.md` go away.
- Tasks live in `bd`. Create with `bd create`, link with `bd dep add`, list ready ones with `bd ready`.
- The loop now does: peek `bd ready --json` → claim the top task with `bd update --claim` → pre-create `.claude/tasks/<id>/` → invoke `claude -p` with the task id → on the next pass, repeat.

The two pieces that make it a fleet:

1. **Unique actor per loop.** Each loop exports `BEADS_ACTOR="${USER}-loop-$$"` so two loops have distinct claim signatures. Beads guarantees only one loop wins the claim.
2. **Failure recovery.** If `claude -p` exits non-zero on a claimed task, the loop releases it back to `ready` (clears the assignee). A single failure doesn't wedge a task in `in_progress` forever.

Add per-iteration logging (`logs/iter-<timestamp>.log`) and you can `tail -f logs/iter-*.log` to watch the fleet in real time.

You can now open three terminals, start `./loop.sh` in each, and let them chew through a queue of independent tasks in parallel. Beads handles dependencies, so a task with unfinished parents won't get picked up until they're closed.

---

## Step 5 — Let the agent stop and ask

It's important to be able to lend the agent a hand when it needs one. `claude -p` can't use the `AskUserQuestion` tool, so we need a substitute.

The fix is a fourth per-task artifact and a protocol:

```
.claude/tasks/<task_id>/Q&A.md
```

When the agent hits an ambiguity it can't resolve from the task description or the codebase, it appends a `## Q:` block — `Context`, `Tried`, `Need` — to `Q&A.md`, then runs `bd update <task_id> --status blocked` and exits.

Three things happen for free:

- `bd ready` stops returning that task. The loop skips it on every pass.
- Other loops keep working on the rest of the queue. One blocked task doesn't stall the fleet.
- You can find pending questions with `bd list --status blocked` or by tailing the logs.

To answer, you open `Q&A.md` in your editor, append an `## A:` block under the `## Q:`, and flip the status back: `bd update <task_id> --status open`. The loop re-picks the task on the next iteration. Claude reads `Q&A.md` first on resume, sees the new `## A:`, and continues — no re-asking, no restart.

The file is **append-only**. Multiple rounds accumulate. You can read the whole back-and-forth later and understand exactly what was decided and why.

Notice what we didn't do: `loop.sh` is byte-identical to step 4's. There's no `--exclude-blocked` flag, no Q&A parser, no notification service. The entire blocking-and-resume flow rides on `bd update --status blocked` plus an append-only file convention in `CLAUDE.md`. The mechanics are pulled apart and live where they belong: the **agent** writes the question, **beads** controls visibility, the **human** answers, the **loop** stays dumb.

---


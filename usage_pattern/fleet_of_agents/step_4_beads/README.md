# Step 4 — Beads queue (parallel loops)

## What this step adds

Replace `TODO.md`/`DONE.md` with `bd` (beads). Beads is a local SQLite-backed task DB with atomic claiming, so multiple `./loop.sh` instances can run in parallel without colliding. The per-task artifact protocol from prior steps is unchanged; the loop now also writes one log file per iteration so you can tail a fleet.

## Files installed

```
loop.sh              ← bd-driven loop: peek → claim → invoke claude → release on failure
.claude/
  CLAUDE.md          ← rules: per-task artifacts + beads task flow + loop awareness
  tasks/             ← per-task subdirectories, pre-created by loop.sh per claimed id
    <task_id>/
      TASK.md                ← one-paragraph restatement of the task
      PLAN_AND_PROGRESS.md   ← numbered checklist with status markers
      FINDINGS.md            ← decisions, results, discoveries (optional)
```

`.beads/` is created by `bd init` (not shipped). `logs/iter-<timestamp>.log` files are written by `loop.sh` at runtime (not shipped).

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

1. Initialize beads and create three tasks (one depends on the other two):

   ```bash
   bd init
   bd create -t "say hi" -p 2
   bd create -t "say bye" -p 2
   bd create -t "summarize" -p 1
   bd dep add bd-3 bd-1 bd-2     # bd-3 depends on bd-1 and bd-2
   ```

2. View the graph and the ready set:

   ```bash
   bd list --tree                # see the dependency graph
   bd ready                      # shows bd-1 and bd-2 (bd-3 is gated on them)
   ```

3. In **one terminal**, start a loop:

   ```bash
   ./loop.sh
   # Loop actor: <user>-loop-12345
   ```

4. In **another terminal**, start a second loop:

   ```bash
   ./loop.sh
   # Loop actor: <user>-loop-67890
   ```

   Confirm the two `BEADS_ACTOR` strings differ. Atomic claiming guarantees no two loops claim the same task id.

5. In a **third terminal**, follow the per-iteration logs:

   ```bash
   tail -f logs/iter-*.log
   ```

6. Once `bd-1` and `bd-2` close, `bd-3` becomes ready and one of the loops will pick it up. When all three are closed, both loops sleep on empty `bd ready`.

### bd command cheatsheet

```bash
bd init                       # initialize beads in the current directory
bd create -t "<title>"        # add a task (use -p <priority> for priority)
bd dep add <child> <parent>   # mark <child> as depending on <parent>
bd list --tree                # visualize the dependency graph
bd ready                      # show tasks ready to claim (no unmet deps, unassigned)
bd show <id>                  # full details for one task
bd close <id> --reason completed   # mark task complete
```

### Failure recovery

If `claude -p` exits non-zero on a claimed task, the loop releases the task back to `ready` (clearing the assignee). You can simulate this by killing `claude -p` mid-iteration — `bd ready` will list the task again on the next loop pass instead of leaving it wedged in `in_progress`.

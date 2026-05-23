# fleet — Python supervisor for headless agent fleets

`fleet` is a lightweight Python supervisor that claims tasks from a
**centralized** [beads](https://github.com/gastownhall/beads) queue and runs
them through a coder adapter (e.g. `claude` CLI) in a headless loop. Each task
remembers the project working directory it was created in, so a single
supervisor can drive work across many projects from one machine.

---

## Installation

Install `fleet` as a global tool so it is on `$PATH` from any directory:

```bash
cd /path/to/fleet
uv tool install --editable .
uv tool update-shell      # if ~/.local/bin is not on PATH yet
```

Then `fleet --help` should work from anywhere. Use `uv tool upgrade fleet`
later to pick up new dependencies; code edits are live because the install is
editable.

Requires:
- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) on your `PATH`
- [beads (`bd`)](https://github.com/gastownhall/beads) on your `PATH`
- `git` on your `PATH` (beads stores its database inside a git repo)

---

## How it works (centralized model)

There is **one** fleet home directory on your machine — `~/.fleet` by default,
override with `$FLEET_HOME` if you like.

```
~/.fleet/
├── .beads/                 # the centralized bd queue (single Dolt DB)
├── runtime.toml            # supervisor config
├── tasks/<task_id>.json    # per-task metadata: {"cwd": "/abs/path/to/project"}
└── logs/                   # supervisor logs
```

Each task records the project working directory the agent should run in
inside `$FLEET_HOME/tasks/<task_id>/task.json` (`{"cwd": "/abs/path"}`).
The supervisor — which can be started from anywhere — claims tasks from
the central queue and runs each agent subprocess in that cwd. Per-task
artifacts (`.claude/tasks/<id>/`) and logs land inside the project the
task points at. If no `task.json` exists for a task, the supervisor falls
back to running the agent in `$FLEET_HOME` itself.

Create tasks with the `fleet bd` passthrough and write `task.json` next to
the new task ID (see "Create your first task" below).

---

## First-run setup

### 1. Initialize the fleet home

```bash
fleet init
# → Fleet home initialized at /Users/you/.fleet
```

This runs `git init` + `bd init` inside `$FLEET_HOME` and writes a default
`runtime.toml`. Idempotent — safe to re-run.

### 2. Install the agent prompt template into each project

The fleet ships a `CLAUDE.md` template that teaches the agent the artifact-dir
continuation model, the Q&A blocking protocol, and the done/failure behaviors.

```bash
cd /path/to/your/project
fleet prompt claude          # writes .claude/CLAUDE.md
fleet prompt agents          # writes AGENTS.md (for non-Claude agents)
```

If `.claude/CLAUDE.md` already exists, `fleet prompt claude` refuses to
overwrite. Re-run with `--force` to replace, or open the bundled template at
`<install>/src/fleet/prompts/CLAUDE.md` and merge by hand.

### 3. Create your first task

Create the task with `fleet bd create` and record the working directory
the supervisor should run it in:

```bash
# 1. Create the task in the central queue.
TASK_ID=$(fleet bd create --title "Implement feature X" --json \
            | jq -r '.data.id')
echo "$TASK_ID"   # e.g. fleet-abc

# 2. Record the project cwd so the supervisor runs the agent there.
mkdir -p "$HOME/.fleet/tasks/$TASK_ID"
printf '{"cwd": "%s"}\n' "$(pwd)" \
    > "$HOME/.fleet/tasks/$TASK_ID/task.json"
```

`fleet bd …` forwards verbatim to the `bd` CLI inside `$FLEET_HOME`, so any
flag `bd create` accepts (`--description`, `--priority`, dependencies via
`bd dep add …`, …) works the same way. Use `$FLEET_HOME` instead of
`$HOME/.fleet` if you have overridden the fleet home.

If you omit step 2 the supervisor still runs the task — it just runs the
agent inside `$FLEET_HOME`, which is rarely what you want.

### 4. Start the supervisor

```bash
fleet run --adapter claude        # foreground; Ctrl+C to stop
fleet run --adapter claude --once # exit when the in-flight queue drains
```

The supervisor reads from `$FLEET_HOME/.beads`, claims ready tasks, and spawns
each agent subprocess in **that task's** working directory.

---

## Command reference

### `fleet init`

```bash
fleet init
fleet init --force        # re-run bd init even if .beads already exists
```

Creates `$FLEET_HOME` (default `~/.fleet`) with a git repo, beads DB, default
`runtime.toml`, and an empty `tasks/` directory.

### `fleet prompt <name>`

Install a bundled prompt template into the current directory.

```bash
fleet prompt claude                       # → .claude/CLAUDE.md
fleet prompt agents                       # → AGENTS.md
fleet prompt claude --force               # overwrite if it exists
fleet prompt claude --dest ./CLAUDE.md    # custom destination
```

### `fleet ready`

```bash
fleet ready
fleet ready --limit 10
```

Lists ready tasks. Each line shows the task ID, title, and recorded cwd.

### `fleet show <id>`

```bash
fleet show fleet-abc
fleet show fleet-abc --json       # raw bd show JSON envelope
```

### `fleet release <id>`

```bash
fleet release fleet-abc
fleet release fleet-abc --reason "needs human review first"
```

### `fleet close <id>`

```bash
fleet close fleet-abc
fleet close fleet-abc --reason "implemented and tested"
```

### `fleet bd <args...>`

Forwards arguments verbatim to the `bd` CLI, executed inside `$FLEET_HOME`.
This is the recommended way to drive the centralized beads queue from any
directory.

```bash
fleet bd create --title "Implement feature X" --json   # → {"data": {"id": "fleet-abc", …}}
fleet bd create --title "Refactor parser" \
    --description "Extract tokenizer to its own file"
fleet bd dep add fleet-newtask fleet-abc               # add dependencies
fleet bd list                                          # list every task in the central DB
fleet bd list --status=blocked                         # filter by status
fleet bd comment fleet-abc "note"                      # comment on a task
fleet bd dolt push                                     # push the beads data to your git remote
fleet bd prime                                         # show beads workflow help
fleet bd --help                                        # bd's own --help (not fleet's)
```

The exit code of `bd` is propagated. All flags are passed through unmodified,
so `fleet bd` behaves exactly like running `bd` from inside `$FLEET_HOME`.

`fleet bd create` does **not** record the agent's working directory.
After creating a task, write `$FLEET_HOME/tasks/<task_id>/task.json` with
the `cwd` you want the supervisor to use:

```bash
mkdir -p "$HOME/.fleet/tasks/$TASK_ID"
printf '{"cwd": "%s"}\n' "$(pwd)" > "$HOME/.fleet/tasks/$TASK_ID/task.json"
```

### `fleet run`

```bash
fleet run --adapter claude
fleet run --adapter claude --once
```

| Option | Description |
|---|---|
| `--adapter` | Coder adapter (required). Use `claude` for the Claude CLI adapter. |
| `--once` | Exit after all currently in-flight tasks finish (no new claims). |

### `fleet config show` / `fleet config set`

```bash
fleet config show
fleet config show --raw                                # raw TOML bytes
fleet config set max_concurrent=5
fleet config set retry_limit=5 rate_limit_threshold_pct=80
```

The supervisor re-reads `$FLEET_HOME/runtime.toml` every
`config_poll_interval_sec` seconds and applies changes without restart.

---

## Configuration reference

All keys live in `$FLEET_HOME/runtime.toml`. Edit via `fleet config set …` or
directly in the file.

| Key | Default | Description |
|---|---|---|
| `max_concurrent` | `3` | Maximum number of agent subprocesses running at once. |
| `rate_limit_threshold_pct` | `90` | Pause claiming new tasks when rate-limit usage exceeds this percentage. |
| `retry_limit` | `3` | Maximum retries per task on non-zero exit. Rate-limit and context-pressure exits do NOT consume a retry. |
| `config_poll_interval_sec` | `5` | How often (seconds) the supervisor re-reads `runtime.toml`. Maximum 10. |
| `claim_poll_interval_sec` | `5` | How often (seconds) the supervisor polls for new claimable tasks. |
| `shutdown_grace_sec` | `30` | How long (seconds) to wait for in-flight tasks to finish on graceful shutdown. |
| `rate_limit_default_sleep_sec` | `300` | Sleep duration (seconds) when a rate-limit pause is triggered. |
| `status_log_interval_sec` | `30` | How often (seconds) the supervisor emits a `supervisor_status` heartbeat with the live in-flight count and rate-limit usage. |
| `artifact_root` | `.claude/tasks` | Directory root where per-task artifact directories are created (relative paths resolve against the task's cwd). |
| `log_root` | `logs` | Root directory for log files (relative paths resolve against the task's cwd). |

---

## Q&A protocol — for the human

When an agent is blocked by ambiguity, it will:

1. Append a `## Q:` block to the task's `Q&A.md` in the artifact directory.
2. Run `bd update <task_id> --status blocked --notes "QUESTION: <summary>"`.
3. Exit cleanly.

**To answer and resume the task:**

1. Find the task:
   ```bash
   fleet ready                  # not listed if blocked
   bd list --status=blocked     # from inside $FLEET_HOME
   fleet show <task_id>         # see the question summary
   ```

2. Locate the artifact directory (inside the task's project, default
   `.claude/tasks/<task_id>/`):
   ```bash
   cat <project>/.claude/tasks/<task_id>/Q\&A.md
   ```

3. Append your answer directly below the `## Q:` block:
   ```markdown
   ## A: <YYYY-MM-DD HH:MM>

   <your answer here>
   ```

4. Unblock the task:
   ```bash
   fleet release <task_id>
   ```

The supervisor will re-claim the task on the next scheduling cycle. The agent
reads `Q&A.md` on startup (per the resume protocol in `CLAUDE.md`) and
continues from where it stopped.

---

## Logs reference

Artifact and log paths are resolved relative to **each task's** cwd (the
project that task targets), so artifacts land next to the code the task is
operating on.

| Path | Contents |
|---|---|
| `<project>/logs/fleet-<date>.jsonl` | Structured supervisor events: claims, releases, retries, rate-limit pauses, shutdowns. |
| `<project>/.claude/tasks/<task_id>/attempt-<n>-<date>.jsonl` | Structured events for one agent subprocess attempt (subprocess stdout is parsed and re-emitted here). |
| `<project>/.claude/tasks/<task_id>/attempt-<n>-<date>.stderr` | Raw stderr of one agent subprocess attempt. |
| `<project>/.claude/tasks/<task_id>/failures.count` | Per-task counter of FAILURE outcomes; drives `retry_limit` exhaustion. |
| `<project>/.claude/tasks/<task_id>/events.jsonl` | Per-task structured events (subset of supervisor events scoped to this task). Agents read this on startup to understand why a prior attempt was interrupted. |
| `<project>/.claude/tasks/<task_id>/PLAN_AND_STATUS.md` | Combined task restatement, plan, and progress marker. Fleet pre-creates a stub; agent populates it and updates after each substantive step. |
| `<project>/.claude/tasks/<task_id>/KNOWLEDGE.md` | Persistent cross-attempt knowledge (surface area, invariants, gotchas). Fleet pre-creates a stub; agent appends as it learns. |
| `<project>/.claude/tasks/<task_id>/Q&A.md` | Q&A thread between agent and human (append-only). |

Change the defaults with `fleet config set artifact_root=<path>` or
`fleet config set log_root=<path>`. Absolute paths skip the per-task
resolution.

### Live fleet status (`supervisor_status` heartbeat)

Every `status_log_interval_sec` seconds (default 30s) the supervisor emits a
`supervisor_status` event to its log and stderr so an operator can answer
"how many tasks are running right now and how close are we to the hourly rate
limit" without re-reading the entire log. Example line (formatted):

```json
{
  "event": "supervisor_status",
  "in_flight": 2,
  "cap": 5,
  "usage_pct": 42.5,
  "threshold_pct": 90,
  "paused_until": null,
  "task_ids": ["fleet-1ps", "fleet-3cg"]
}
```

The same `in_flight` / `usage_pct` fields are also attached to each
`task_claimed`, `task_completed_success`, `task_failure_release`,
`task_retry_exhausted`, `task_context_pressure_release`,
`task_blocked_by_agent`, and `task_rate_limit_release` event so every
lifecycle line is self-describing.

---

## FAQ

**Q: A task exhausted its retries. What now?**

The supervisor moves the task to `blocked` with a reason of the form
`"retry limit (N) exhausted; last failure: …"` and posts a comment with
the last exit code and a tail of stderr. Inspect the failure logs in
`<project>/.claude/tasks/<task_id>/attempt-*-<date>.{jsonl,stderr}` (the
project is shown by `fleet show <task_id>`). Fix the underlying issue, then:

```bash
fleet release <task_id>
```

The supervisor will re-claim it with a fresh retry counter.

---

**Q: How do rate-limit pauses work?**

When the Claude API rate-limit usage exceeds `rate_limit_threshold_pct`, the
supervisor stops claiming new tasks. In-flight tasks continue running. The
supervisor resumes claiming after `rate_limit_default_sleep_sec` seconds (or
when the rate gauge drops below the threshold). Rate-limit exits do NOT
consume a retry.

---

**Q: Can I run the fleet across multiple machines?**

Multi-machine operation is out of scope for v1. The supervisor is designed for
single-machine use. The beads queue is a local Dolt database; concurrent access
from multiple machines is not supported in this version.

---

**Q: Why is there no `--resume` flag?**

The fleet does not pass `--resume` to the Claude CLI. Continuation state lives
entirely in the artifact directory (`PLAN_AND_STATUS.md`, `KNOWLEDGE.md`,
`Q&A.md`, `events.jsonl`). The agent reads these files on every fresh
invocation to pick up where it left off. This approach works across restarts,
crashes, and machine reboots without depending on the CLI's session
resumption mechanism.

---

**Q: Where is the bundled `CLAUDE.md` template?**

Use `fleet prompt claude` to drop it into the current directory. The source
lives at `<install>/src/fleet/prompts/CLAUDE.md` if you prefer to read it
first. Fleet does **not** auto-install or merge it — that's intentional, since
`.claude/CLAUDE.md` is your file and auto-merge could clobber custom
instructions.

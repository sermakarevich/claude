# fleet — Python supervisor for headless agent fleets

`fleet` is a lightweight Python supervisor that claims tasks from a
[beads](https://github.com/gastownhall/beads) queue and runs them through a
coder adapter (e.g. `claude` CLI) in a headless loop.

---

## Installation

```bash
# Install dependencies into .venv (uses uv)
just sync          # or: uv sync
```

Requires:
- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) and [`just`](https://github.com/casey/just) on your `PATH`
- [beads (`bd`)](https://github.com/gastownhall/beads) on your `PATH`

All examples below assume you run them from this directory (`fleet/`). The
`just` recipes wrap `uv run fleet …`; pick whichever style you prefer.

---

## First-run setup

### 1. Initialize beads in your project

```bash
cd /path/to/your/project
bd init
```

### 2. View (and optionally edit) the default config

```bash
just config           # or: uv run fleet config show
```

This creates `.fleet/runtime.toml` with defaults if it does not exist yet.

### 3. Copy the agent prompt template into your project

The fleet ships a `CLAUDE.md` template that teaches the agent the artifact-dir
continuation model, the Q&A blocking protocol, and the done/failure behaviors.

```bash
# The bundled template lives at:
#   fleet/src/fleet/prompts/CLAUDE.md
cp src/fleet/prompts/CLAUDE.md .claude/CLAUDE.md
```

If your project already has a `.claude/CLAUDE.md`, merge the relevant sections
into it rather than overwriting.

### 4. Create your first task

```bash
just create "Implement feature X"      # or: uv run fleet create "Implement feature X"
# Prints the new task ID, e.g. beads-abc
```

### 5. Start the supervisor

```bash
just run              # or: uv run fleet run --adapter claude
just run-once         # exit when the queue drains
```

The supervisor claims ready tasks, spawns agent subprocesses, and loops until
interrupted (`Ctrl+C`).

---

## Command reference

All commands work via either `just <recipe>` or `uv run fleet <subcommand>`. The
`just` form is shorter; the `uv run` form lets you pass arbitrary flags.

### Create a task — `just create` / `fleet create`

```bash
just create "Write unit tests for module Y"
uv run fleet create "Refactor parser" --description "Extract tokenizer to its own file"
uv run fleet create "Task C" --depends-on beads-abc --depends-on beads-def
uv run fleet create "Fix bug" --label hotfix --label backend
```

| Option | Description |
|---|---|
| `--description`, `-d` | Task description |
| `--depends-on` | IDs this task depends on (repeatable) |
| `--label` | Labels to attach (repeatable) |

### List ready tasks — `just ready` / `fleet ready`

```bash
just ready
uv run fleet ready --limit 10
```

### Show a task — `just show <id>` / `fleet show <id>`

```bash
just show beads-abc
uv run fleet show beads-abc --json   # raw bd show JSON
```

### Release a task — `just release <id>` / `fleet release <id>`

```bash
just release beads-abc
just release beads-abc "needs human review first"
```

### Close a task — `just close <id>` / `fleet close <id>`

```bash
just close beads-abc
just close beads-abc "implemented and tested"
```

### Run the supervisor — `just run` / `fleet run`

```bash
just run                              # default adapter: claude
just run-once                         # exit after in-flight count drops to 0
uv run fleet run --adapter claude     # explicit form
```

| Option | Description |
|---|---|
| `--adapter` | Coder adapter (required). Use `claude` for the Claude CLI adapter. |
| `--once` | Exit after all currently in-flight tasks finish (no new claims). |

### Show config — `just config` / `fleet config show`

```bash
just config
uv run fleet config show --raw    # raw TOML bytes
```

### Set config — `just set <key>=<val> …` / `fleet config set …`

Update one or more config keys atomically. The supervisor picks up changes
within `config_poll_interval_sec` seconds without restart.

```bash
just set max_concurrent=5
just set retry_limit=5 rate_limit_threshold_pct=80
```

---

## Configuration reference

All keys live in `.fleet/runtime.toml`. Edit via `just set …` (or `uv run fleet
config set …`) or directly in the file; the supervisor re-reads it every
`config_poll_interval_sec` seconds.

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
| `artifact_root` | `.claude/tasks` | Directory root where per-task artifact directories are created. |
| `log_root` | `logs` | Root directory for log files. |

---

## Q&A protocol — for the human

When an agent is blocked by ambiguity, it will:

1. Append a `## Q:` block to the task's `Q&A.md` in the artifact directory.
2. Run `bd update <task_id> --status blocked --notes "QUESTION: <summary>"`.
3. Exit cleanly.

**To answer and resume the task:**

1. Find the task:
   ```bash
   bd list --status=blocked
   bd show <task_id>   # see the question summary in notes
   ```

2. Locate the artifact directory (default: `.claude/tasks/<task_id>/`):
   ```bash
   cat .claude/tasks/<task_id>/Q&A.md
   ```

3. Append your answer directly below the `## Q:` block:
   ```markdown
   ## A: <YYYY-MM-DD HH:MM>

   <your answer here>
   ```

4. Unblock the task:
   ```bash
   bd update <task_id> --status open
   ```

The supervisor will re-claim the task on the next scheduling cycle. The agent
reads `Q&A.md` on startup (per the resume protocol in `CLAUDE.md`) and
continues from where it stopped.

---

## Logs reference

| Path | Contents |
|---|---|
| `logs/fleet-<date>.jsonl` | Structured supervisor events: claims, releases, retries, rate-limit pauses, shutdowns. |
| `.claude/tasks/<task_id>/attempt-<n>-<date>.jsonl` | Structured events for one agent subprocess attempt (subprocess stdout is parsed and re-emitted here). |
| `.claude/tasks/<task_id>/attempt-<n>-<date>.stderr` | Raw stderr of one agent subprocess attempt. |
| `.claude/tasks/<task_id>/failures.count` | Per-task counter of FAILURE outcomes; drives `retry_limit` exhaustion. |
| `.claude/tasks/<task_id>/events.jsonl` | Per-task structured events (subset of supervisor events scoped to this task). Agents read this on startup to understand why a prior attempt was interrupted. |
| `.claude/tasks/<task_id>/PLAN_AND_STATUS.md` | Combined task restatement, plan, and progress marker. Fleet pre-creates a stub; agent populates it and updates after each substantive step. |
| `.claude/tasks/<task_id>/KNOWLEDGE.md` | Persistent cross-attempt knowledge (surface area, invariants, gotchas). Fleet pre-creates a stub; agent appends as it learns. |
| `.claude/tasks/<task_id>/Q&A.md` | Q&A thread between agent and human (append-only). |

The artifact root can be changed via `just set artifact_root=<path>`.
The log root can be changed via `just set log_root=<path>`.

### Live fleet status (`supervisor_status` heartbeat)

Every `status_log_interval_sec` seconds (default 30s) the supervisor emits a
`supervisor_status` event to `logs/fleet-<date>.jsonl` and stderr so an
operator can answer "how many tasks are running right now and how close are
we to the hourly rate limit" without re-reading the entire log. Example
line (formatted):

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
lifecycle line is self-describing. Tail the heartbeat with:

```bash
tail -f logs/fleet-$(date +%F).jsonl | jq -c 'select(.event == "supervisor_status") | {in_flight, cap, usage_pct, paused_until}'
```

---

## FAQ

**Q: A task exhausted its retries. What now?**

The supervisor moves the task to `blocked` with a reason of the form
`"retry limit (N) exhausted; last failure: …"` and posts a comment with
the last exit code and a tail of stderr. Check
`.claude/tasks/<task_id>/attempt-*-<date>.{jsonl,stderr}` for the failure
logs. Fix the underlying issue (missing context, bad task description,
code bug), then:

```bash
bd update <task_id> --status open
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

```
fleet/src/fleet/prompts/CLAUDE.md
```

Copy it into your project's `.claude/CLAUDE.md` (or merge it with an existing
one). The fleet does **not** auto-install or merge it — that's intentional,
since `.claude/CLAUDE.md` is your file and auto-merge could clobber custom
instructions.

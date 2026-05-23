# fleet — Python supervisor for headless agent fleets

`fleet` is a lightweight Python supervisor that claims tasks from a
[beads](https://github.com/gastownhall/beads) queue and runs them through a
coder adapter (e.g. `claude` CLI) in a headless loop.

---

## Installation

```bash
# From the repo root (editable install)
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

Requires Python ≥ 3.11 and [beads (`bd`)](https://github.com/gastownhall/beads)
on your `PATH`.

---

## First-run setup

### 1. Initialize beads in your project

```bash
cd /path/to/your/project
bd init
```

### 2. View (and optionally edit) the default config

```bash
fleet config show
```

This creates `.fleet/runtime.toml` with defaults if it does not exist yet.

### 3. Copy the agent prompt template into your project

The fleet ships a `CLAUDE.md` template that teaches the agent the artifact-dir
continuation model, the Q&A blocking protocol, and the done/failure behaviors.

```bash
# Find the bundled template
python -c "import fleet; from pathlib import Path; print(Path(fleet.__file__).parent / 'prompts' / 'CLAUDE.md')"

# Copy into your project (merge with existing .claude/CLAUDE.md if present)
cp <path-above> .claude/CLAUDE.md
```

If your project already has a `.claude/CLAUDE.md`, merge the relevant sections
into it rather than overwriting.

### 4. Create your first task

```bash
fleet create "Implement feature X"
# Prints the new task ID, e.g. beads-abc
```

### 5. Start the supervisor

```bash
fleet run --adapter claude
```

The supervisor claims ready tasks, spawns agent subprocesses, and loops until
interrupted (`Ctrl+C`).

---

## Command reference

### `fleet create <title>`

Create a new task in beads.

```bash
fleet create "Write unit tests for module Y"
fleet create "Refactor parser" --description "Extract tokenizer to its own file"
fleet create "Task C" --depends-on beads-abc --depends-on beads-def
fleet create "Fix bug" --label hotfix --label backend
```

| Option | Description |
|---|---|
| `--description`, `-d` | Task description |
| `--depends-on` | IDs this task depends on (repeatable) |
| `--label` | Labels to attach (repeatable) |

### `fleet ready`

List tasks that are ready to be claimed (no unresolved dependencies).

```bash
fleet ready
fleet ready --limit 10
```

### `fleet show <task-id>`

Show one task's details.

```bash
fleet show beads-abc
fleet show beads-abc --json   # raw bd show JSON
```

### `fleet release <task-id>`

Release a task back to open status.

```bash
fleet release beads-abc
fleet release beads-abc --reason "needs human review first"
```

### `fleet close <task-id>`

Mark a task as complete (terminal state).

```bash
fleet close beads-abc
fleet close beads-abc --reason "implemented and tested"
```

### `fleet run`

Start the fleet supervisor.

```bash
fleet run --adapter claude
fleet run --adapter claude --once   # exit after in-flight count drops to 0
```

| Option | Description |
|---|---|
| `--adapter` | Coder adapter (required). Use `claude` for the Claude CLI adapter. |
| `--once` | Exit after all currently in-flight tasks finish (no new claims). |

### `fleet config show`

Print the current runtime configuration.

```bash
fleet config show          # formatted table
fleet config show --raw    # raw TOML bytes
```

### `fleet config set <key>=<value>`

Update one or more config keys atomically. The supervisor picks up changes
within `config_poll_interval_sec` seconds without restart.

```bash
fleet config set max_concurrent=5
fleet config set retry_limit=5 rate_limit_threshold_pct=80
```

---

## Configuration reference

All keys live in `.fleet/runtime.toml`. Edit via `fleet config set` or directly
in the file; the supervisor re-reads it every `config_poll_interval_sec` seconds.

| Key | Default | Description |
|---|---|---|
| `max_concurrent` | `3` | Maximum number of agent subprocesses running at once. |
| `rate_limit_threshold_pct` | `90` | Pause claiming new tasks when rate-limit usage exceeds this percentage. |
| `retry_limit` | `3` | Maximum retries per task on non-zero exit. Rate-limit and context-pressure exits do NOT consume a retry. |
| `config_poll_interval_sec` | `5` | How often (seconds) the supervisor re-reads `runtime.toml`. Maximum 10. |
| `claim_poll_interval_sec` | `5` | How often (seconds) the supervisor polls for new claimable tasks. |
| `shutdown_grace_sec` | `30` | How long (seconds) to wait for in-flight tasks to finish on graceful shutdown. |
| `rate_limit_default_sleep_sec` | `300` | Sleep duration (seconds) when a rate-limit pause is triggered. |
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
| `logs/attempts/<task_id>/<attempt_n>.log` | Raw stdout+stderr of each agent subprocess attempt. |
| `logs/fleet-<date>.jsonl` | Structured supervisor events: claims, releases, retries, rate-limit pauses, shutdowns. |
| `.claude/tasks/<task_id>/events.jsonl` | Per-task structured events (subset of supervisor events scoped to this task). Agents read this on startup to understand why a prior attempt was interrupted. |
| `.claude/tasks/<task_id>/PLAN.md` | Agent-written task plan. |
| `.claude/tasks/<task_id>/STATE.md` | Agent-written progress state. |
| `.claude/tasks/<task_id>/Q&A.md` | Q&A thread between agent and human. |

The artifact root can be changed via `fleet config set artifact_root=<path>`.
The log root can be changed via `fleet config set log_root=<path>`.

---

## FAQ

**Q: A task exhausted its retries. What now?**

The task is released with a `retry_exhausted` reason and left in `blocked`
state. Check `logs/attempts/<task_id>/` for the failure logs. Fix the
underlying issue (missing context, bad task description, code bug), then:

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
entirely in the artifact directory (`PLAN.md`, `STATE.md`, `Q&A.md`,
`events.jsonl`). The agent reads these files on every fresh invocation to pick
up where it left off. This approach works across restarts, crashes, and
machine reboots without depending on the CLI's session resumption mechanism.

---

**Q: Where is the bundled `CLAUDE.md` template?**

```bash
python -c "import fleet; from pathlib import Path; print(Path(fleet.__file__).parent / 'prompts' / 'CLAUDE.md')"
```

Copy it into your project's `.claude/CLAUDE.md` (or merge it with an existing
one). The fleet does **not** auto-install or merge it — that's intentional,
since `.claude/CLAUDE.md` is your file and auto-merge could clobber custom
instructions.

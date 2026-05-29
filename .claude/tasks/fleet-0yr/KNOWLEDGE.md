# fleet-0yr — KNOWLEDGE

## Surface area
- `fleet/src/fleet/runner.py` — `TaskRunner.run`: creates artifact_dir, stubs,
  attempt logs, checks `.context_pressure`.
- `fleet/src/fleet/queue.py` — `BeadsQueue._meta_path` / `_load_meta` /
  `_write_meta`: stores per-task metadata (currently flat `<id>.json`).
- `fleet/src/fleet/attempts.py` — `count_attempts` / `failure_count` /
  `increment_failure`: operate on artifact_dir.
- `fleet/src/fleet/logging_setup.py` — `open_attempt_log`, `append_event`:
  write per-attempt JSONL/stderr and events.jsonl into artifact_dir.
- `fleet/src/fleet/supervisor.py` — `_spawn_runner` passes `project_root=task.cwd`
  to runner; `_artifact_dir_for` resolves the artifact path from config.
- `fleet/src/fleet/adapters/claude_cli.py` — `env()` exports
  `FLEET_TASK_ID`, `FLEET_ARTIFACT_DIR`, `FLEET_ATTEMPT`.
- `fleet/src/fleet/hooks/precompact.sh` — touches
  `$FLEET_ARTIFACT_DIR/.context_pressure` on PreCompact.
- `fleet/src/fleet/config.py` — `artifact_root` defaults to `.claude/tasks`.
- `fleet/src/fleet/prompts/CLAUDE.md` + `AGENTS.md` — outdated wrt actual
  stub filenames (mention `PLAN.md` / `STATE.md`, but runner writes
  `PLAN_AND_STATUS.md` / `KNOWLEDGE.md`).
- Tests touching the old layout: `test_runner.py`, `test_attempts.py`,
  `test_logging.py`, `test_queue.py`, `tests/integration/test_task_cwd.py`,
  `tests/integration/conftest.py` (uses `.fleet/runtime.toml` under tmp_path).

## Invariants
- Subprocess CWD must remain `task.cwd` (FR contract; integration test
  `test_task_runs_in_its_own_cwd` covers it).
- In-flight subprocesses must never be killed by config changes (FR-26/27).
- `events.jsonl` is append-only across attempts.
- The CLAUDE.md "read these files first" section must remain the first `##`
  block (enforced by `test_read_files_first_is_first_section`).

## Gotchas
- `BeadsQueue._meta_path` currently returns `<repo_root>/tasks/<id>.json`. The
  integration test (`test_task_runs_in_its_own_cwd`) asserts
  `project_dir / ".claude" / "tasks" / task.id` exists, so it needs updating
  to the new centralized path.
- `_ensure_artifact_stubs` is idempotent (never overwrites) — preserve that.
- The PreCompact hook depends on an env var to know where to write
  `.context_pressure`. Updating the env contract requires updating the hook
  script in lockstep, otherwise `test_context_pressure_returns_context_pressure`
  will fail.
- Config knob `artifact_root` is referenced from runner and supervisor; removing
  it requires updating both readers and `test_config.py` defaults.

# fleet-7jv — STATE

**Status:** completed

## Done
- Moved per-attempt logs and failure counter into `.claude/tasks/<task_id>/`:
  - `attempt-<n>-<date>.jsonl`
  - `attempt-<n>-<date>.stderr`
  - `failures.count`
- API now takes `artifact_dir` directly (drops `task_id` from filename since
  the directory already scopes by task).
- Files changed:
  - `src/fleet/logging_setup.py` — `open_attempt_log(artifact_dir, …)`.
  - `src/fleet/attempts.py` — `count_attempts`, `failure_count`,
    `increment_failure` all take `artifact_dir`.
  - `src/fleet/runner.py` — drop `log_root` field, pass `artifact_dir`.
  - `src/fleet/supervisor.py` — add `_artifact_dir_for(task_id)`; use it for
    `increment_failure`; drop `log_root` from `TaskRunner` constructor call.
  - `README.md` — logs reference + FAQ updated.
- Tests updated:
  - `tests/test_attempts.py` — rewritten around `artifact_dir`.
  - `tests/test_logging.py` — `open_attempt_log` invocations.
  - `tests/test_supervisor_failures.py` — `failure_count` calls use
    `_artifact_dir_for`.
  - `tests/integration/test_failure_retry.py` — `failure_count` / `count_attempts`.
  - `tests/integration/test_context_pressure.py` — `failure_count`.
  - `tests/integration/test_qa_flow.py` — `failure_count`.
- All 215 tests pass (`uv run pytest`).

## In progress
- none

## Blocked
- none

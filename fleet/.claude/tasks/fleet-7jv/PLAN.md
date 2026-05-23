# fleet-7jv · Plan

## Problem
Per-attempt logs currently live in `logs/attempts/<task_id>-attempt-<n>-<date>.{jsonl,stderr}`
and the failure counter in `logs/attempts/<task_id>-failures.count`. The user
wants per-task attempt logs to live alongside the rest of the per-task state
in `.claude/tasks/<task_id>/`. Supervisor-wide logs (`logs/fleet-<date>.jsonl`)
stay in `log_root`; only the per-task files move.

## Target layout (per task)
```
.claude/tasks/<task_id>/
  attempt-<n>-<date>.jsonl       (was logs/attempts/<task_id>-attempt-<n>-<date>.jsonl)
  attempt-<n>-<date>.stderr      (was logs/attempts/<task_id>-attempt-<n>-<date>.stderr)
  failures.count                 (was logs/attempts/<task_id>-failures.count)
  events.jsonl                   (unchanged)
  PLAN.md, STATE.md, Q&A.md      (unchanged)
```

`task_id` is no longer in the filename because the directory already scopes
the files to a single task.

## Steps
1. `src/fleet/logging_setup.py` — change `open_attempt_log(log_root, …)` →
   `open_attempt_log(artifact_dir, …)`; write `<artifact_dir>/attempt-<n>-<date>.{jsonl,stderr}`.
2. `src/fleet/attempts.py` — change all three helpers to take `artifact_dir`:
   - `count_attempts(artifact_dir)` globs `attempt-*-*.jsonl` directly.
   - `failure_count(artifact_dir)` reads `<artifact_dir>/failures.count`.
   - `increment_failure(artifact_dir)` writes `<artifact_dir>/failures.count`.
3. `src/fleet/runner.py` — compute `artifact_dir` first, then pass it to
   `count_attempts` and `open_attempt_log`. Drop `log_root` field (no longer
   needed by runner once attempts move).
4. `src/fleet/supervisor.py` — add `_artifact_dir_for(task_id)` resolver;
   use it for `increment_failure` in `_handle_outcome`. Pass `artifact_root`
   into `TaskRunner` (replacing `log_root`).
5. Update tests:
   - `tests/test_attempts.py`
   - `tests/test_logging.py`
   - `tests/test_runner.py` (drop `log_root` kwarg if removed)
   - `tests/test_supervisor_failures.py`
   - `tests/integration/test_failure_retry.py`
6. Update `README.md` logs reference and FAQ.
7. Run `just test` to confirm no regressions.

## Verification
- All existing unit + integration tests pass.
- Manual: `uv run fleet run --once` on a small task writes attempt log into
  `.claude/tasks/<task_id>/attempt-1-<date>.jsonl` (not `logs/attempts/`).

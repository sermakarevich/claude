# fleet-1ps — PLAN_AND_STATUS

## Restatement
Improve fleet supervisor logging so an operator can see, at a glance, (1) how
many tasks are currently in flight and (2) what fraction of the hourly
rate-limit budget has been consumed. The data is already tracked internally
(`Supervisor.in_flight`, `RateGauge.current_pct()`) but is only surfaced when a
task is claimed or when a rate-limit pause/resume occurs — so during steady
state the operator sees nothing.

## Plan
1. Add a `status_log_interval_sec` knob to `RuntimeConfig` (default 30s).
2. Add a `_status_log_loop` background task to `Supervisor` that emits a
   `supervisor_status` structlog event every interval with:
   - `in_flight` (count) and `cap` (max_concurrent)
   - `usage_pct` (from `rate_gauge.current_pct()`) and `threshold_pct`
   - `paused_until` (ISO string or null)
   - `task_ids` (list of in-flight task IDs, for visibility)
3. Enrich existing per-task lifecycle logs (`task_claimed`, the four outcomes)
   with `usage_pct` so each lifecycle event tells the full picture.
4. Tests: assert the heartbeat fires, includes the right fields, and survives
   shutdown cleanly.
5. Update `README.md` operator section to document the new heartbeat event.

## Status
**Status:** completed

### Done
- Reviewed surface area: `supervisor.py`, `rate_gauge.py`, `config.py`,
  `supervisor_spawn.py`, `logging_setup.py`.
- Added `status_log_interval_sec` (default 30s) to `RuntimeConfig` and
  `_KEY_TYPES` in `src/fleet/config.py`.
- Added `_status_log_loop` background task wired into `Supervisor.run()`
  alongside the existing claim/reap/config-poll loops.
- Added `_fleet_log_context()` helper that snapshots in-flight count, cap,
  usage_pct, threshold_pct, paused_until, and task_ids.
- `_log_status_snapshot()` emits a `supervisor_status` event via the
  supervisor logger; line goes to `logs/fleet-<date>.jsonl` and stderr.
- Enriched `task_claimed`, `task_completed_success`,
  `task_completed_success_re_queued`, `task_context_pressure_release`,
  `task_blocked_by_agent`, `task_rate_limit_release`, `task_retry_exhausted`,
  and `task_failure_release` with `usage_pct` + `in_flight` + `cap` so each
  lifecycle line is self-describing.
- Resolved `paused_until` kwarg collision in `task_rate_limit_release`.
- Wrote 11 new tests in `tests/test_supervisor_status_log.py` covering the
  config knob default + override, snapshot fields, heartbeat firing on
  interval, clean shutdown, and outcome-log enrichment.
- Updated `README.md`: added `status_log_interval_sec` row in the config
  table and a "Live fleet status (`supervisor_status` heartbeat)" section
  in Logs reference with a JSON example and a `tail -f | jq` recipe.
- Quality gates: all 226 tests pass (unit + integration).

### In progress
- none

### Blocked
- none

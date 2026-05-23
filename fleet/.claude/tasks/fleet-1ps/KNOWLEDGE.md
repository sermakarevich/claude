# fleet-1ps — KNOWLEDGE

## Surface area
- `src/fleet/supervisor.py` — owns `in_flight`, `rate_gauge`, the bg loops
  (`_claim_and_spawn_loop`, `_reap_loop`, `_config_poll_loop`). Add the new
  `_status_log_loop` here.
- `src/fleet/rate_gauge.py` — `RateGauge.current_pct()` returns the live
  usage %, auto-resets to 0 once `resets_at + 5s` has passed.
- `src/fleet/config.py` — `RuntimeConfig` dataclass + `_KEY_TYPES` map.
  Adding a new knob requires updating both.
- `src/fleet/logging_setup.py` — structlog setup; supervisor logger writes
  to `logs/fleet-<date>.jsonl` and stderr (tee).
- `src/fleet/supervisor_spawn.py` — `SpawnController` already emits
  `rate_limit_pause`/`rate_limit_resume` events but only on transitions.

## Invariants
- `Supervisor.in_flight` is the canonical count of running task subprocesses.
- `RateGauge.current_pct()` is safe to call at any time; it self-resets after
  the reset window passes.
- New background loops must respect `self._shutting_down` and exit cleanly so
  shutdown grace works (see existing loops as the pattern).
- New config keys must be added to both `RuntimeConfig` and `_KEY_TYPES`.

## Gotchas
- `claim_poll_interval_sec` defaults to 5s; if the heartbeat interval is
  shorter than the poll, the heartbeat would dominate the log. Default to 30s.
- Tests using `_make_supervisor` build the supervisor without running
  `run()`, so the new bg loop must not run automatically at construction.
- `RuntimeConfig` is a frozen-ish dataclass with default values; new fields
  need defaults to keep existing test construction (`RuntimeConfig(retry_limit=3)`)
  working.
- `task_rate_limit_release` log already passes its own `paused_until` (str
  of datetime), which collides with the same key in `_fleet_log_context()`.
  Filter it out via `{k: v for k, v in fleet_ctx.items() if k != "paused_until"}`
  before splatting.

## Summary
Operator visibility gap closed: a `supervisor_status` heartbeat now emits
every `status_log_interval_sec` (default 30s) with in-flight count, cap,
usage_pct, threshold_pct, paused_until, and task_ids. The same fleet-stat
fields ride along on every task lifecycle event so each line is
self-describing.

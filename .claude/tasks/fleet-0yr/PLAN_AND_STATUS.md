# fleet-0yr — PLAN_AND_STATUS

## Restatement
Centralize every task's filesystem state under `$FLEET_HOME/tasks/<id>/` with
three slots: `task.json` (metadata: title, description, cwd, status),
`attempts/` (supervisor-private per-attempt logs + events.jsonl +
failures.count + transient flags), and `artifacts/` (agent-facing
`PLAN_AND_STATUS.md` + `KNOWLEDGE.md` and other Markdown). Update the bundled
`CLAUDE.md` / `AGENTS.md` prompts so they point agents at the new layout
(including replacing the pre-existing `PLAN.md` / `STATE.md` references with
the actual `PLAN_AND_STATUS.md` filename the runner creates).

## Plan
1. Layout: `<fleet_home>/tasks/<id>/{task.json,attempts/,artifacts/}`.
   - `attempts/` holds `events.jsonl`, `attempt-N-DATE.jsonl`,
     `attempt-N-DATE.stderr`, `failures.count`, `.context_pressure`.
   - `artifacts/` holds `PLAN_AND_STATUS.md`, `KNOWLEDGE.md`, and any
     agent-written files (Q&A.md etc).
2. Env contract: introduce `FLEET_TASK_DIR` (task root); keep
   `FLEET_ARTIFACT_DIR` but point it at the `artifacts/` subfolder.
3. Queue (`queue.py`):
   - Replace `<repo_root>/tasks/<id>.json` (flat) with
     `<repo_root>/tasks/<id>/task.json`.
   - Record `title`, `description`, `status`, `cwd` in `task.json` (mirror of
     beads) and rewrite it on every `claim_next`/`get`/`create_task` round-trip
     so it stays fresh.
4. Runner (`runner.py`): write attempt logs/events to `<task_dir>/attempts/`;
   stubs to `<task_dir>/artifacts/`; look for `.context_pressure` under
   `attempts/`.
5. Attempts helpers (`attempts.py`): operate on `<task_dir>/attempts/`.
6. Logging (`logging_setup.py`): `open_attempt_log` + `append_event` write to
   the attempts sub-directory.
7. Supervisor (`supervisor.py`): pass `fleet_home` to the runner; subprocess
   still runs in `task.cwd`; `_artifact_dir_for` returns the new task dir.
8. Adapter (`claude_cli.py`): export `FLEET_TASK_DIR` + point
   `FLEET_ARTIFACT_DIR` at `artifacts/`.
9. Hook (`precompact.sh`): touch `$FLEET_TASK_DIR/attempts/.context_pressure`.
10. Prompts (`prompts/CLAUDE.md`, `prompts/AGENTS.md`): describe the new layout
    and switch to `PLAN_AND_STATUS.md` / `KNOWLEDGE.md` naming.
11. Config (`config.py`): drop the `artifact_root` knob — it's always
    `<fleet_home>/tasks/<id>/` now.
12. Update every test that references the old paths
    (`.claude/tasks/<id>/{events.jsonl,attempt-*.jsonl,PLAN_AND_STATUS.md,…}`)
    or the old `<repo_root>/tasks/<id>.json` meta file.

## Status
**Status:** in_progress

### Done
- Explored existing structure, identified all touch points (runner, queue,
  attempts, logging, supervisor, adapter, hooks, prompts, config, tests).
- Source-side restructure already landed: queue uses `<root>/tasks/<id>/task.json`;
  runner writes attempt logs/events to `<task_dir>/attempts/`; runner exports
  `FLEET_TASK_DIR` + `FLEET_ARTIFACT_DIR=<task_dir>/artifacts/`; hook touches
  `$FLEET_TASK_DIR/attempts/.context_pressure`; prompts updated to new layout;
  `artifact_root` config knob dropped.

### In progress
- Updating tests that still reference old paths:
  - `test_queue.py` (flat `<id>.json` meta paths) → nested `<id>/task.json`.
  - `test_runner.py` StubAdapter env() needs to expose `FLEET_TASK_DIR`.
  - `test_adapter_claude.py` env-var assertions for new task_dir contract.
  - `test_hooks.py` precompact env now uses `FLEET_TASK_DIR` + `attempts/`.
  - `test_supervisor_failures.py` `_artifact_dir_for` → `_task_dir_for`.
  - `test_cli_config.py` no `artifact_root` in defaults output.
  - `test_config.py` `artifact_root` assertion needs removal.
  - Integration tests (`test_failure_retry.py`, `test_context_pressure.py`,
    `test_qa_flow.py`, `test_task_cwd.py`) point at old
    `<project>/.claude/tasks/<id>/{events.jsonl,…}`; switch to
    `<fleet_home>/tasks/<id>/{artifacts,attempts}/…`.
  - `fake_claude.py` `context_pressure` scenario writes the flag to
    `FLEET_ARTIFACT_DIR` but it now must go to `FLEET_TASK_DIR/attempts/`.
- Rename adapter interface parameter `artifact_dir` → `task_dir` for clarity.

### Blocked
- none

# fleet-jb2 — PLAN_AND_STATUS

## Restatement
Add a `fleet bd` subcommand that forwards all trailing arguments verbatim to
the `bd` CLI, executed with `cwd=$FLEET_HOME`. This lets users operate the
centralized beads queue (list, comment, dolt push, prime, etc.) from any
directory without `cd $FLEET_HOME` first.

## Plan
1. Add a `bd` typer command in `fleet/src/fleet/cli.py`. ✅
2. Add CLI tests in `fleet/tests/test_cli.py`. ✅
3. Document the command in `fleet/README.md`. ✅
4. Run the full test suite. ✅
5. Close the beads task.

## Status
**Status:** completed

### Done
- Added `bd` passthrough subcommand at `fleet/src/fleet/cli.py:212-227`
  using `context_settings={"allow_extra_args": True,
  "ignore_unknown_options": True, "help_option_names": []}`. Subprocess
  inherits the parent stdin/stdout/stderr; returncode propagated via
  `typer.Exit`.
- Added 4 CLI tests in `fleet/tests/test_cli.py` (arg forwarding + cwd,
  exit-code propagation, `--help` pass-through, listed in `fleet --help`).
- Documented `fleet bd <args...>` in `fleet/README.md` with examples
  (list, comment, dolt push, prime, --help).
- Full suite green: 234 passed.
- Live smoke test in a temp FLEET_HOME: `fleet bd list` → "No issues
  found."; `fleet bd` → bd's own help; exit 0.

### In progress
- none

### Blocked
- none

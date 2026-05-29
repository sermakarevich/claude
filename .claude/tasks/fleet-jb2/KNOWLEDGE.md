# fleet-jb2 — KNOWLEDGE

## Surface area
- `fleet/src/fleet/cli.py` — added `bd_passthrough` typer command.
- `fleet/tests/test_cli.py` — added 4 tests for the passthrough.
- `fleet/README.md` — added a `### fleet bd <args...>` section in the
  command reference, before `### fleet run`.

## Invariants
- The passthrough must run with `cwd=$FLEET_HOME` (resolved via
  `_fleet_home()`), not the caller's `$PWD`. Otherwise bd will fall back
  to auto-discovery and may pick a different `.beads` DB.
- `subprocess.run` for the passthrough does NOT capture stdout/stderr —
  it inherits the parent streams so colored bd output and progress
  reach the user.
- The bd exit code must be propagated unmodified (`typer.Exit(rc)`).

## Gotchas
- Click/typer eagerly handle `--help` and `-h` for each command, which
  prevents passthrough of those flags. Suppress this by setting
  `"help_option_names": []` in `context_settings`. With that, `fleet bd
  --help` correctly invokes `bd --help`.
- `"allow_extra_args": True` alone is not enough — also need
  `"ignore_unknown_options": True` so flags like `--limit 5` are not
  treated as typer options.
- The `subprocess.run` cwd parameter accepts a `pathlib.Path`; tests
  compare against `Path(tmp_path).resolve()` since `_fleet_home()`
  calls `.resolve()`.

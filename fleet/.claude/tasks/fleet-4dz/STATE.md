# fleet-4dz · State

## Status: FIXED

## Change
`tests/integration/test_dynamic_config.py::test_dynamic_config_new_cap_respected_after_completion`

Replaced the brittle `await asyncio.sleep(6.0)` with a deterministic poll
loop that waits up to 15s for `len(sup.in_flight) <= 2`, then a 2s stable
window to detect any unwanted re-spawn. Updated the misleading "~7s
already elapsed" comment.

## Verification
- Failing repro confirmed pre-fix (`got 3 <= 2` AssertionError).
- Post-fix: 3/3 isolated runs PASSED at ~14.4s each.
- Full `tests/integration/test_dynamic_config.py` (3 tests) PASSED at 26.27s.

## Files Touched
- `tests/integration/test_dynamic_config.py` — only file edited.
- `.claude/tasks/fleet-4dz/PLAN.md`, `.claude/tasks/fleet-4dz/STATE.md` — artifacts.

## Notes
The test file remains untracked in the broader repo state (alongside other
in-progress work). The fix is applied on-disk; commit scope is the file
edit + artifacts.

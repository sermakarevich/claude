# fleet-4dz · Plan

## Problem
`test_dynamic_config_new_cap_respected_after_completion` fails consistently
locally. Timing margins too tight: only t-000 reliably completes by assertion
time (~11–12s elapsed) while the slow scenario sleeps 10s per task and tasks
are claimed ~1s apart (t-001 ends t≈11s, t-002 t≈12s, t-003 t≈13s).

## Fix Strategy
Replace the fixed `await asyncio.sleep(6.0)` with deterministic polling that
waits for `in_flight` to drop to ≤2 (the new cap), then verifies the cap
holds for a stable window. This is faster on average, robust on slow
machines, and documents the test invariant clearly.

## Steps
1. Edit `tests/integration/test_dynamic_config.py` in
   `test_dynamic_config_new_cap_respected_after_completion`:
   - Replace `await asyncio.sleep(6.0)` with a polling loop that waits up to
     ~15s for `len(sup.in_flight) <= 2`.
   - Add a short stable-window sleep (~2s) to allow any unwanted spawns to
     surface.
   - Update misleading "~7s already elapsed" comment.
2. Run the failing test in isolation to confirm fix.
3. Run the full `tests/integration/test_dynamic_config.py` file to confirm
   no regressions in adjacent tests.
4. Close `fleet-4dz`, commit, push.

## Verification
- Re-run `uv run pytest tests/integration/test_dynamic_config.py -xvs`.
- Expect all 3 tests in file to pass.

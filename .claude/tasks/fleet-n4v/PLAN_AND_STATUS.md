# fleet-n4v — PLAN_AND_STATUS

## Restatement
Validate whether `fleet/src/fleet/prompts/` (containing `CLAUDE.md` + `AGENTS.md`)
is redundant with the project-root `fleet/CLAUDE.md` + `fleet/AGENTS.md`, or
whether both must be kept.

## Plan
1. Read both pairs of files to compare content.
2. Find every code reference to the `prompts/` directory.
3. Inspect the install flow and `pyproject.toml` packaging.
4. Decide: keep, merge, or delete `prompts/`.

## Status
**Status:** completed

### Done
- Compared the two pairs of files — content is unrelated.
- Mapped all references (`cli.py:26`, `pyproject.toml:25`, README, test_docs.py).
- Verified `prompts/*.md` is shipped as package-data in the wheel.
- Verdict written to REPORT.md.

### In progress
- none

### Blocked
- none

## Verdict (short)
KEEP the `prompts/` folder. The two file pairs serve different audiences:

| Location | Audience | Purpose |
|---|---|---|
| `fleet/CLAUDE.md`, `fleet/AGENTS.md` (repo root) | Agents developing the fleet codebase itself | Build/test, beads tracker, project conventions |
| `fleet/src/fleet/prompts/CLAUDE.md`, `…/AGENTS.md` | End-user projects that install fleet | The **Fleet Task Protocol** — PLAN/STATE/Q&A resume protocol, retry semantics, hook restrictions |

The `prompts/` files are package-data (`pyproject.toml:25`: `fleet = [..., "prompts/*.md"]`)
loaded at install time by the `fleet prompt claude` / `fleet prompt agents`
CLI commands (`cli.py:26` `_PROMPTS_DIR`, `cli.py:331-346`). Removing them
breaks: the install CLI, the README-documented onboarding flow (README.md:71-127),
and `tests/test_docs.py` (which asserts the exact paths and content shape).

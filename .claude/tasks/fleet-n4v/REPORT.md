# fleet-n4v — Validation Report

**Question:** Do we still need `fleet/src/fleet/prompts/` if we already have
`CLAUDE.md` and `AGENTS.md` at the fleet project root?

**Answer:** Yes — keep both. They are not duplicates; they serve different
audiences and live in different lifecycle layers.

---

## 1. What the two pairs actually contain

### Repo-root pair — `fleet/CLAUDE.md`, `fleet/AGENTS.md`
- Beads issue-tracker quick reference (`bd ready`, `bd close`, etc.)
- Session-completion / git-push checklist for developers
- Build & Test stubs, architecture overview, conventions
- Non-interactive shell-command rules

**Audience:** any AI agent (Claude Code, Codex, etc.) doing development
work on the fleet source tree.

### Package pair — `fleet/src/fleet/prompts/CLAUDE.md`, `…/AGENTS.md`
- The **Fleet Task Protocol**:
  - "On every fresh start, read these files first" (PLAN/STATE/Q&A/events)
  - How to write progress (PLAN.md, STATE.md)
  - `bd close` on completion
  - Q&A blocking protocol (`## Q:` → `bd update --status blocked`)
  - `AskUserQuestion` is denied by a PreToolUse hook
  - Failure / retry / rate-limit semantics

**Audience:** the headless subprocess agent that the fleet *supervisor*
spawns inside an end-user's project.

There is **zero content overlap** between the two pairs.

## 2. How the package pair is wired in

| File | Purpose |
|---|---|
| `src/fleet/cli.py:26` | `_PROMPTS_DIR = Path(__file__).parent / "prompts"` |
| `src/fleet/cli.py:307-346` | `_install_prompt`, `prompt claude`, `prompt agents` CLI commands copy `prompts/*.md` into a user project's `.claude/CLAUDE.md` / `AGENTS.md` |
| `src/fleet/adapters/claude_cli.py:27` | Spawned-agent prompt: *"Follow the Loop Task Protocol in CLAUDE.md"* — the installed copy of `prompts/CLAUDE.md` |
| `pyproject.toml:25` | `fleet = ["hooks/*.sh", "prompts/*.md"]` ships the templates as wheel package-data |
| `tests/test_docs.py:9-10, 96-118` | Hard-asserts the paths `prompts/CLAUDE.md`, `prompts/AGENTS.md` and content invariants |
| `README.md:71-127, 363-368` | Documents `fleet prompt claude/agents` as the user onboarding flow |

## 3. What breaks if you delete `prompts/`

1. `fleet prompt claude` / `fleet prompt agents` raise `Error: bundled template not found` and exit 1 (`cli.py:309-311`).
2. The wheel ships no Fleet Task Protocol — users have no canonical template to install into their projects.
3. Spawned subprocess agents have no PLAN/STATE/Q&A resume protocol to follow → retries restart from scratch, blocked tasks have no Q&A channel.
4. `tests/test_docs.py` (≥9 tests) fail immediately.
5. The README onboarding section is stale and broken.

## 4. Could we collapse them?

No, for two independent reasons:

- **Different content.** The repo-root files cover dev workflow (beads,
  build/test, push). The package files cover runtime protocol (resume,
  Q&A, retry). Merging would either bloat the dev docs with runtime
  details that don't apply to humans, or pollute the runtime protocol
  with dev-only beads/git rules that confuse the subprocess.
- **Packaging boundary.** Package-data must live under the importable
  `fleet/` package directory (`src/fleet/...`). The repo-root files are
  not shipped to PyPI; moving runtime templates to the root would
  silently strip them from installs.

## 5. Optional improvement (not required)

If the name collision is confusing, the `prompts/` files could be renamed
to make their role obvious — e.g. `prompts/task_protocol_claude.md` and
`prompts/task_protocol_agents.md`. That would require updating
`cli.py:337,346`, `tests/test_docs.py:9-10`, and the README. It is purely
cosmetic; the current structure is correct.

---

## Verdict

**KEEP `fleet/src/fleet/prompts/`.** It is the package-bundled Fleet Task
Protocol that ships in the wheel and is installed into user projects by
`fleet prompt claude` / `fleet prompt agents`. The repo-root `CLAUDE.md` /
`AGENTS.md` are unrelated developer-facing project instructions. Removing
either set breaks a distinct, real-world flow.

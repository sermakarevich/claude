# fleet-n4v — KNOWLEDGE

## Surface area
- `fleet/CLAUDE.md`, `fleet/AGENTS.md` — repo-root dev instructions (beads,
  build/test, conventions). Audience: agents working ON fleet's source.
- `fleet/src/fleet/prompts/CLAUDE.md`, `…/AGENTS.md` — bundled package
  resource. Audience: spawned subprocess agents in *user* projects that
  consume fleet. Contains the Fleet Task Protocol (PLAN/STATE/Q&A resume,
  retry semantics, AskUserQuestion ban).
- `fleet/src/fleet/cli.py:26` — `_PROMPTS_DIR = Path(__file__).parent / "prompts"`.
- `fleet/src/fleet/cli.py:307-346` — `_install_prompt`, `prompt claude`,
  `prompt agents` commands copy `prompts/*.md` into a target project.
- `fleet/src/fleet/adapters/claude_cli.py:27` — spawned-agent prompt
  references "the Loop Task Protocol in CLAUDE.md", i.e. the file that
  `fleet prompt claude` installed from `prompts/CLAUDE.md`.
- `fleet/pyproject.toml:25` — `fleet = ["hooks/*.sh", "prompts/*.md"]`
  package-data so the templates ship in the wheel.
- `fleet/tests/test_docs.py:9-10` — hard-codes `prompts/CLAUDE.md` and
  `prompts/AGENTS.md` paths and asserts content invariants.
- `fleet/README.md:71-127, 363-368` — documents `fleet prompt claude/agents`
  and points users at `<install>/src/fleet/prompts/CLAUDE.md` to read or
  hand-merge.

## Invariants
- The two prompt files (`prompts/CLAUDE.md`, `prompts/AGENTS.md`) must stay
  in sync; `AGENTS.md` is the same content for non-Claude adapters with a
  short header note. Asserted indirectly by test_docs.py.
- "Read these files first" must remain the first `##` section of
  `prompts/CLAUDE.md` (test_docs.py: `test_read_files_first_is_first_section`).
- Templates must be installable as package-data — they live inside the
  importable `fleet` package directory, not in the repo root.

## Gotchas
- The two file pairs look alike (both named CLAUDE.md / AGENTS.md) but have
  zero shared content. The repo-root ones are checked-in dev docs; the
  `prompts/` ones are shipped to users.
- Deleting `prompts/` would break: the `fleet prompt` CLI subcommands, the
  documented user onboarding (README), `test_docs.py`, and ultimately the
  resume protocol that spawned tasks rely on inside user projects (because
  there would be no template to install).
- Renaming/merging the root files into `prompts/` would invert the
  packaging boundary — package-data must live under `src/fleet/`, not at
  the repo root.

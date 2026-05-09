# shortcuts

A Claude Code hook that turns prefixes like `fix:` or `q:` into background `claude -p` extractions. Each shortcut binds a **prefix** to its own **system prompt**, **output file**, and **event** (`UserPromptSubmit` to capture user intent, `Stop` to capture the model's reply). When a prompt matches, the hook forks a Haiku call that merges the new content into the output file.

## How it works

```
hook event (UserPromptSubmit | Stop)
  └─► hook.py
       ├─ dispatch by hook_event_name
       │   ├─ UserPromptSubmit → match shortcut prefix at start of prompt
       │   └─ Stop → read transcript_path, find last user prompt + last assistant text
       ├─ resolve dst: absolute → global; relative → resolved against the main session's cwd (parent dir auto-created)
       ├─ fork to background (parent returns immediately — no delay to user)
       └─ child: `claude -p --model haiku` with shortcut.prompt_path as system prompt
                 └─► merged rewrite OR `NONE`
                 └─► write to shortcut.output_path
```

- **Trigger**: regex `^\s*<prefix>\s*` per shortcut, case-insensitive. The prefix is stripped before being sent to the extractor.
- **Extractor**: `claude -p --model haiku` — shells out to Claude Code headless mode, reusing your existing auth. **No `ANTHROPIC_API_KEY` required.**
- **Background execution**: the hook forks after the match. Parent exits instantly, child spends 2-5s talking to Haiku and writing the file. Your prompt turn is never delayed.
- **Path resolution**: relative `output_path` → resolved against the main session's cwd (parent dir auto-created); absolute `output_path` → global.
- **Recursion guard**: the hook sets `SHORTCUTS_INSIDE=1` for the spawned `claude -p` so it can't recursively re-trigger itself, plus a `ps`-based ancestor check.

## Built-in shortcuts

### `fix:` — durable instructions (UserPromptSubmit)

Captures corrections, preferences, and project facts into per-repo `.claude/artifacts/INSTRUCTIONS.md`, auto-imported by that repo's root `CLAUDE.md`.

- `fix: always prefer polars over pandas` → captured as a preference
- `fix: this repo uses Dynaconf for config merging` → captured as a project fact
- `fix: this NPE in auth.py` → extractor returns `NONE` (one-off, not durable)
- `please fix the test` → not triggered (doesn't start with `fix:`)
- `let's fix: X` → not triggered (`fix:` must be at the very start)

### `q:` — Q&A capture (Stop)

When a prompt starts with `q:`, the **main session** answers it normally — then the Stop hook reads the transcript, grabs the assistant's reply, and appends a `## Q&A` entry to per-repo `.claude/artifacts/Q&A.md`.

- `q: what's the difference between dataclass(frozen=True) and NamedTuple?` → main session answers; Stop hook stores Q + summarized A + full reply (collapsible) in `Q&A.md`.

This is the right pattern when you want the **main session's** answer (full context, tools, history) — not an isolated `claude -p` lookup.

## Adding a new shortcut

1. Drop a system prompt at `prompts/<name>.md`. It should describe what to extract from the input and the exact shape of the output file. The hook injects context as `REPO`, `EXISTING content of <filename>`, and `NEW INPUT`.
2. Append a `Shortcut(...)` to `SHORTCUTS` in `constants.py`. Example for a global knowledge base:
   ```python
   Shortcut(
       prefix="kb:",
       prompt_path=PROMPTS_DIR / "kb.md",
       output_path=Path.home() / ".claude" / "knowledge_base.md",  # absolute → global, no opt-in
       event=EVENT_PROMPT,  # or EVENT_STOP to capture the model's reply
   ),
   ```
3. The hook is already registered globally for both events, so new shortcuts pick up immediately.

## Install

**Prereqs**: `jq`, `claude` CLI, `python3` (stdlib only — no pip installs).

```bash
# one-time, user-global: registers UserPromptSubmit + Stop hooks (idempotent + migration-aware)
~/git/claude/hooks/shortcuts/install.sh
```

That's it. After install, `fix:` and `q:` work in any session — the hook resolves relative `output_path`s against the main session's cwd and creates parent dirs on first use. The model itself creates the artifact file (and, for `fix:`, adds the `@.claude/artifacts/INSTRUCTIONS.md` import to `CLAUDE.md`) on the first matching prompt.

`install.sh` is idempotent: it preserves unrelated hooks (e.g. activity loggers) and replaces any prior registration of this hook under either event.

## Files

```
shortcuts/
├── hook.py            # the dispatcher (UserPromptSubmit + Stop), stdlib only
├── constants.py       # config: Shortcut dataclass, SHORTCUTS list, model, log path, env-var sentinels
├── install.sh         # one-time global registration for both events
├── prompts/
│   ├── fix.md         # system prompt for `fix:`
│   └── q.md           # system prompt for `q:`
└── README.md
```

Per repo (auto-created by the model on first matching prompt):
```
<repo>/
├── CLAUDE.md                                # gets `@.claude/artifacts/INSTRUCTIONS.md` (added by `fix:`)
└── .claude/
    └── artifacts/
        ├── INSTRUCTIONS.md                  # maintained by `fix:`
        └── Q&A.md                           # maintained by `q:`
```

## Debugging

Logs: `hooks/shortcuts/logs/hook.log` (every invocation logs `event=...`; failures and outcomes follow).

Manual foreground dry-run for `fix:`:
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"fix: always use polars","cwd":"/path/to/opted-in-repo"}' \
  | SHORTCUTS_NO_FORK=1 python3 ~/git/claude/hooks/shortcuts/hook.py
```

Manual foreground dry-run for `q:` (point at any real transcript JSONL):
```bash
echo '{"hook_event_name":"Stop","cwd":"/path/to/opted-in-repo","transcript_path":"/path/to/transcript.jsonl"}' \
  | SHORTCUTS_NO_FORK=1 python3 ~/git/claude/hooks/shortcuts/hook.py
```

If nothing happens after a real prompt:
- Check `hook.log` for trigger/extraction messages.
- Confirm the prefix is at the **start of the prompt** (whitespace before is OK).
- Confirm `claude -p` works: `echo hi | claude -p --model haiku --output-format text`.

## Tuning

- **Model**: edit `MODEL` in `constants.py` (default `haiku`).
- **Shortcuts**: edit the `SHORTCUTS` list in `constants.py`.
- **Per-shortcut behavior**: edit the matching `prompts/<name>.md`. The extractor treats that file as its contract.
- **Timeout / size caps**: `TIMEOUT_SECONDS`, `MAX_EXISTING_CHARS`, `MAX_ANSWER_CHARS` in `constants.py`.

## Uninstall

Manually remove the `python3 ".../shortcuts/hook.py"` entries from both the `UserPromptSubmit` and `Stop` arrays in `~/.claude/settings.json`. Per-repo `CLAUDE.md` imports and artifact files can stay or be deleted.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

MODEL = "opus"
MAX_EXISTING_CHARS = 50_000
MAX_ANSWER_CHARS = 20_000  # cap assistant text fed to the extractor for Stop shortcuts
TIMEOUT_SECONDS = 120  # `claude -p` can vary 3-60s; give generous headroom

NO_FORK_ENV = "SHORTCUTS_NO_FORK"

EVENT_PROMPT = "UserPromptSubmit"
EVENT_STOP = "Stop"

SCRIPT_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"
LOG_PATH = SCRIPT_DIR / "logs" / "hook.log"


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG_PATH.open("a") as f:
        f.write(f"{ts} {msg}\n")


@dataclass(frozen=True)
class Shortcut:
    prefix: str           # matched at line start, case-insensitive, whitespace-trimmed
    prompt_path: Path     # md file: instruction (inject) or system prompt (extract)
    output_path: Path     # absolute → global; relative → resolved against the main session's cwd (parent dir auto-created)
    action: Callable[..., None]  # called with (shortcut, content, cwd, dst); see actions.py
    event: str = EVENT_PROMPT  # EVENT_PROMPT (capture intent) or EVENT_STOP (capture model's reply)
    header: str = ""           # seeded into output_path when the file doesn't exist yet
    claude_md_import: str = "" # ensured present in <cwd>/CLAUDE.md, else <cwd>/.claude/CLAUDE.md (created)


# Late import: actions.py imports scalars from this module, so resolve action
# references after the scalars are defined.
from actions import inject_instruction  # noqa: E402

SHORTCUTS: list[Shortcut] = [
    # `fix:` — capture durable instructions/preferences. Per-repo, opt-in via install.sh.
    Shortcut(
        prefix="fix:",
        prompt_path=PROMPTS_DIR / "fix.md",
        output_path=Path(".claude") / "artifacts" / "INSTRUCTIONS.md",
        action=inject_instruction,
        header="# Instructions\n\n## Corrections\n\n",
        claude_md_import="@.claude/artifacts/INSTRUCTIONS.md",
    ),
    # `q:` — capture (question, answer) pairs from the main session into a per-repo notebook.
    Shortcut(
        prefix="q:",
        prompt_path=PROMPTS_DIR / "q.md",
        output_path=Path(".claude") / "artifacts" / "Q&A.md",
        action=inject_instruction,
        header="# Q&A\n\n",
    ),
]

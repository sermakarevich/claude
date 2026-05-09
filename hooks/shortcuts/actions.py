"""Stock actions for shortcuts. An action receives (shortcut, content, cwd, dst) and
performs whatever side-effect the shortcut wants. Add new actions here."""

from __future__ import annotations

import json
import os
import subprocess
import traceback
from pathlib import Path

from constants import (
    EVENT_PROMPT,
    MAX_EXISTING_CHARS,
    MODEL,
    NO_FORK_ENV,
    TIMEOUT_SECONDS,
    Shortcut,
    log,
)


def inject_instruction(*, shortcut: Shortcut, content: str, cwd: str, dst: Path) -> None:
    """Read instruction md, substitute {dst}, emit as additionalContext on stdout.
    Claude Code injects this into the main session for the same turn — the model
    does the work in-line, no subprocess, no Stop-event timing."""
    template = shortcut.prompt_path.read_text()
    instruction = template.replace("{dst}", str(dst))
    payload = {
        "hookSpecificOutput": {
            "hookEventName": EVENT_PROMPT,
            "additionalContext": instruction,
        }
    }
    print(json.dumps(payload))
    log(f"{cwd}: `{shortcut.prefix}` → injected (dst={dst}, content={content[:60]!r})")


def extract_via_claude_p(*, shortcut: Shortcut, content: str, cwd: str, dst: Path) -> None:
    """Fork (unless NO_FORK) and run `claude -p` with the shortcut's md as system prompt;
    write the merged result to dst. Use for shortcuts that need an isolated, deterministic
    pass over an accumulating file."""
    if os.environ.get(NO_FORK_ENV):
        _run_extractor(shortcut, content, cwd, dst)
        return

    pid = os.fork()
    if pid > 0:
        return

    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    os.close(devnull)

    try:
        _run_extractor(shortcut, content, cwd, dst)
    except Exception as e:
        log(f"{cwd}: `{shortcut.prefix}` extraction failed: {e}\n{traceback.format_exc()}")
    os._exit(0)


def _run_extractor(shortcut: Shortcut, content: str, cwd: str, dst: Path) -> None:
    existing = dst.read_text() if dst.exists() else ""
    if len(existing) > MAX_EXISTING_CHARS:
        existing = existing[-MAX_EXISTING_CHARS:]

    system_prompt = shortcut.prompt_path.read_text()
    user_msg = (
        f"REPO: {cwd}\n\n"
        f"EXISTING content of {shortcut.output_path.name}:\n"
        "<existing>\n"
        f"{existing if existing.strip() else '(empty)'}\n"
        "</existing>\n\n"
        f"NEW INPUT (from `{shortcut.prefix}` shortcut, prefix stripped):\n"
        "<input>\n"
        f"{content}\n"
        "</input>\n"
    )
    full_prompt = f"{system_prompt}\n\n{user_msg}"

    result = subprocess.run(
        ["claude", "-p", "--model", MODEL, full_prompt],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p exit={result.returncode}: {result.stderr.strip()[:500]}"
        )
    merged = _strip_code_fences(result.stdout.strip())
    if merged.strip().upper() == "NONE" or not merged.strip():
        log(f"{cwd}: `{shortcut.prefix}` → NONE")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(merged.rstrip() + "\n")
    log(f"{cwd}: `{shortcut.prefix}` → updated {dst}")


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        _, _, s = s.partition("\n")
    if s.rstrip().endswith("```"):
        s = s.rstrip()[:-3].rstrip()
    return s

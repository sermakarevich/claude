#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from constants import (
    EVENT_PROMPT,
    EVENT_STOP,
    MAX_ANSWER_CHARS,
    SHORTCUTS,
    Shortcut,
    log,
)


def match_shortcut(prompt: str, event: str) -> tuple[Shortcut, str] | None:
    """Return (shortcut, stripped_prompt) for the first prefix matching the given event, or None."""
    for shortcut in SHORTCUTS:
        if shortcut.event != event:
            continue
        pattern = re.compile(rf"^\s*{re.escape(shortcut.prefix)}\s*", re.IGNORECASE)
        m = pattern.match(prompt)
        if m:
            return shortcut, prompt[m.end():].strip()
    return None


def resolve_dst(shortcut: Shortcut, cwd: str) -> Path:
    """Absolute output_path → return as-is. Relative output_path → resolve against
    the main session's cwd and ensure the parent directory exists. If the shortcut
    declares a header and the file is missing, seed it so the prompt only has to
    describe the entry shape, not the bootstrap."""
    if shortcut.output_path.is_absolute():
        dst = shortcut.output_path
    else:
        dst = Path(cwd) / shortcut.output_path
        dst.parent.mkdir(parents=True, exist_ok=True)
    if shortcut.header and not dst.exists():
        dst.write_text(shortcut.header)
    return dst


def ensure_claude_md_import(shortcut: Shortcut, cwd: str) -> None:
    """Make sure `shortcut.claude_md_import` (e.g. `@.claude/artifacts/INSTRUCTIONS.md`)
    appears in a CLAUDE.md that Claude Code will load. Lookup order:
      1. <cwd>/CLAUDE.md if it exists,
      2. else <cwd>/.claude/CLAUDE.md if it exists,
      3. else create <cwd>/.claude/CLAUDE.md.
    Idempotent — adds the line only if absent."""
    line = shortcut.claude_md_import.strip()
    if not line:
        return
    root = Path(cwd) / "CLAUDE.md"
    nested = Path(cwd) / ".claude" / "CLAUDE.md"
    target = root if root.exists() else nested
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text() if target.exists() else ""
    if any(l.strip() == line for l in existing.splitlines()):
        return
    sep = "" if not existing or existing.endswith("\n") else "\n"
    target.write_text(existing + sep + line + "\n")


def read_last_exchange(transcript_path: Path) -> tuple[str, str] | None:
    """Walk JSONL forward; return (last_user_text_prompt, joined_assistant_text_after).
    Skips user entries whose content is a list (those are tool_result envelopes, not typed prompts).
    Also recognizes queued_command attachments — mid-turn messages stored as attachment.prompt
    rather than as type=user entries."""
    try:
        lines = transcript_path.read_text().splitlines()
    except Exception as e:
        log(f"failed to read transcript {transcript_path}: {e}")
        return None

    user_prompt: str | None = None
    assistant_chunks: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        t = entry.get("type")
        msg = entry.get("message") or {}
        if t == "user":
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                user_prompt = content
                assistant_chunks = []  # new turn → reset captured assistant text
        elif t == "attachment":
            att = entry.get("attachment") or {}
            if att.get("type") == "queued_command":
                prompt_text = att.get("prompt")
                if isinstance(prompt_text, str) and prompt_text.strip():
                    user_prompt = prompt_text
                    assistant_chunks = []
        elif t == "assistant" and user_prompt is not None:
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text") or ""
                        if text.strip():
                            assistant_chunks.append(text)

    if user_prompt is None or not assistant_chunks:
        return None
    return user_prompt, "\n\n".join(assistant_chunks)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        log(f"bad stdin: {e}")
        return

    event = payload.get("hook_event_name") or EVENT_PROMPT
    if event == EVENT_PROMPT:
        handle_prompt_submit(payload)
    elif event == EVENT_STOP:
        handle_stop(payload)
    # else: silently ignore unknown events


def handle_prompt_submit(payload: dict) -> None:
    prompt = payload.get("prompt") or ""
    cwd = payload.get("cwd") or os.getcwd()

    match = match_shortcut(prompt, EVENT_PROMPT)
    if match is None:
        return
    shortcut, stripped = match
    log(f"{cwd}: caught `{shortcut.prefix}` event={EVENT_PROMPT}")
    if not stripped:
        log(f"{cwd}: empty content after stripping `{shortcut.prefix}`")
        return

    dispatch(shortcut=shortcut, content=stripped, cwd=cwd)


def handle_stop(payload: dict) -> None:
    cwd = payload.get("cwd") or os.getcwd()
    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return
    tx = Path(transcript_path)
    if not tx.exists():
        return

    exchange = read_last_exchange(tx)
    if exchange is None:
        return
    user_prompt, assistant_text = exchange

    match = match_shortcut(user_prompt, EVENT_STOP)
    if match is None:
        return
    shortcut, stripped_question = match
    log(f"{cwd}: caught `{shortcut.prefix}` event={EVENT_STOP}")
    if not stripped_question:
        log(f"{cwd}: empty question after stripping `{shortcut.prefix}`")
        return

    if len(assistant_text) > MAX_ANSWER_CHARS:
        assistant_text = assistant_text[:MAX_ANSWER_CHARS] + "\n\n...[truncated]"

    content = (
        f"QUESTION:\n{stripped_question}\n\n"
        f"ANSWER:\n{assistant_text}"
    )
    dispatch(shortcut=shortcut, content=content, cwd=cwd)


def dispatch(shortcut: Shortcut, content: str, cwd: str) -> None:
    """Resolve destination (relative paths land under the main session's cwd), make
    sure any required CLAUDE.md @import is wired up, then delegate to the action."""
    dst = resolve_dst(shortcut, cwd)
    ensure_claude_md_import(shortcut, cwd)
    shortcut.action(shortcut=shortcut, content=content, cwd=cwd, dst=dst)


if __name__ == "__main__":
    main()

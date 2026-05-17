#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp>=1.0.0",
# ]
# ///
"""MCP server exposing Claude Code as a delegated-agent tool.

Wraps `claude -p` (headless mode). Lets a third-party MCP-speaking agent —
another agent like hermes, a local Ollama-backed assistant, etc. — delegate
work to Claude Code over the user's existing Claude subscription rather than
spending its own API credits or hitting the capability ceiling of a small
local model.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

CLAUDE_BIN = os.environ.get("CLAUDE_CODE_MCP_BIN") or shutil.which("claude") or "claude"

PERMISSION_MODES = ("acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan")

mcp = FastMCP(
    "claude_code",
    instructions=(
        "Delegate tasks to a headless Claude Code session. Intended for "
        "third-party MCP-speaking agents — e.g. hermes, or a local Ollama-"
        "backed agent — to route work through the user's existing Claude "
        "Code subscription instead of spending their own API credits or "
        "being limited by a small local model. Pass a prompt and optional "
        "knobs (cwd, model, allowed/disallowed tools, system-prompt "
        "appendix, permission mode, resume session id). Returns the final "
        "reply along with session_id, cost, duration, and turn count. Reuse "
        "session_id to continue a prior conversation."
    ),
)


def _build_cmd(
    allowed_tools: list[str] | None,
    disallowed_tools: list[str] | None,
    append_system_prompt: str | None,
    model: str | None,
    resume_session: str | None,
    permission_mode: str | None,
    add_dir: list[str] | None,
) -> list[str]:
    # Prompt is piped via stdin (not a positional arg) so variadic flags like
    # --add-dir don't slurp it.
    cmd: list[str] = [CLAUDE_BIN, "-p", "--output-format", "json"]
    if allowed_tools:
        cmd += ["--allowed-tools", ",".join(allowed_tools)]
    if disallowed_tools:
        cmd += ["--disallowed-tools", ",".join(disallowed_tools)]
    if append_system_prompt:
        cmd += ["--append-system-prompt", append_system_prompt]
    if model:
        cmd += ["--model", model]
    if resume_session:
        cmd += ["--resume", resume_session]
    if permission_mode:
        if permission_mode not in PERMISSION_MODES:
            raise ValueError(
                f"Invalid permission_mode '{permission_mode}'. "
                f"Allowed: {', '.join(PERMISSION_MODES)}."
            )
        cmd += ["--permission-mode", permission_mode]
    if add_dir:
        cmd += ["--add-dir", *add_dir]
    return cmd


@mcp.tool()
def ask_claude(
    prompt: str,
    cwd: str | None = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    append_system_prompt: str | None = None,
    model: str | None = None,
    resume_session: str | None = None,
    permission_mode: str | None = None,
    add_dir: list[str] | None = None,
    timeout: float | None = None,
) -> dict:
    """Run a one-shot Claude Code session and return its final reply.

    Args:
        prompt: The task or question to send to Claude.
        cwd: Working directory Claude runs in (controls relative file paths,
            git context, project-scoped settings/CLAUDE.md discovery).
        allowed_tools: Tool allowlist (e.g. ["Read", "Bash(git *)", "Edit"]).
        disallowed_tools: Tool denylist; same format as `allowed_tools`.
        append_system_prompt: String appended to Claude's default system prompt.
        model: Model alias ("opus", "sonnet", "haiku") or full ID.
        resume_session: UUID of a prior session to continue.
        permission_mode: One of "acceptEdits", "auto", "bypassPermissions",
            "default", "dontAsk", "plan". Headless sessions can't show prompts,
            so non-trivial tool use usually needs "acceptEdits" or an
            `allowed_tools` allowlist.
        add_dir: Extra directories outside `cwd` that tools may access.
        timeout: Seconds to wait before killing the subprocess. None = no limit.

    Returns:
        On success: the JSON object emitted by `claude -p --output-format json`
        — fields include `result` (the final reply), `session_id`, `num_turns`,
        `duration_ms`, `total_cost_usd`, `is_error`.

        On failure: {"is_error": true, "error": str, "stderr": str, "stdout": str}.
    """
    try:
        cmd = _build_cmd(
            allowed_tools=allowed_tools,
            disallowed_tools=disallowed_tools,
            append_system_prompt=append_system_prompt,
            model=model,
            resume_session=resume_session,
            permission_mode=permission_mode,
            add_dir=add_dir,
        )
    except ValueError as e:
        return {"is_error": True, "error": str(e)}

    if cwd is not None and not Path(cwd).is_dir():
        return {"is_error": True, "error": f"cwd '{cwd}' is not a directory"}

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "is_error": True,
            "error": f"`claude` binary not found at '{CLAUDE_BIN}'. "
                     "Install Claude Code or set CLAUDE_CODE_MCP_BIN.",
        }
    except subprocess.TimeoutExpired as e:
        return {
            "is_error": True,
            "error": f"claude exceeded timeout of {timeout}s",
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
        }

    if proc.returncode != 0:
        return {
            "is_error": True,
            "error": f"claude exited with code {proc.returncode}",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "is_error": True,
            "error": "could not parse claude output as JSON",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }


@mcp.tool()
def claude_version() -> str:
    """Return the version string of the `claude` binary this server wraps."""
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return f"Error: `claude` not found at '{CLAUDE_BIN}'."
    return (proc.stdout or proc.stderr).strip()


if __name__ == "__main__":
    mcp.run()

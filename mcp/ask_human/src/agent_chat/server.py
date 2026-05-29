#!/usr/bin/env python3
"""MCP server letting headless agents ask a human operator and block for the answer.

Subagents and Workflow agents cannot use Claude Code's ``AskUserQuestion`` tool
(it is filtered out at the system level). They *can* call MCP tools, and an MCP
tool is allowed to block until it returns. This server records each question in
a shared SQLite store (see ``store.py``) and blocks until a human answers it via
any operator frontend — the ``agent-chat`` CLI/TUI or the web dashboard — then
returns the answer to the calling agent.

Run standalone:  uv run python -m agent_chat.server   (stdio transport)
"""

from __future__ import annotations

from typing import Any, Optional, Union

from mcp.server.fastmcp import FastMCP

from .store import QuestionStore

store = QuestionStore()

mcp = FastMCP(
    "ask_human",
    instructions=(
        "Reach a human operator for decisions you cannot make on your own. Call "
        "`ask_human_question` whenever you need human judgment, approval, or missing "
        "information to proceed instead of guessing — it records the question and "
        "BLOCKS until a person answers from a separate operator console, then returns "
        "their answer. Pass `options` for a multiple-choice decision, or omit them for "
        "free-text input. On unattended runs always set `timeout_s` and a `default` so "
        "you never block forever."
    ),
)


def _result(q: dict) -> dict[str, Any]:
    """Project a stored question down to what the calling agent needs."""
    return {
        "id": q["id"],
        "status": q["status"],          # answered | expired | cancelled
        "answer": q["answer"],          # str, list[str] (multi_select), or None
        "answered_by": q.get("answered_by"),
    }


@mcp.tool()
def ask_human_question(
    prompt: str,
    options: Optional[list[str]] = None,
    multi_select: bool = False,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout_s: Optional[float] = None,
    default: Optional[Union[str, list[str]]] = None,
    priority: int = 0,
) -> dict[str, Any]:
    """Ask the human operator a question and BLOCK until they answer.

    Args:
        prompt: The question to show the operator.
        options: Optional list of choices. Omit for a free-text answer.
        multi_select: If true, the operator may pick several options.
        agent_id: Label for who is asking (e.g. the subagent/task label) so the
            operator can tell concurrent questions apart.
        session_id: Optional grouping key (e.g. the workflow run id).
        timeout_s: Give up after this many seconds. Strongly recommended for
            unattended runs. On timeout the question expires and `default` is
            returned as the answer.
        default: Answer to return if `timeout_s` elapses with no human response.
        priority: Higher numbers surface first in the operator's queue.

    Returns:
        {"id", "status", "answer", "answered_by"}. `status` is "answered",
        "expired" (timed out — `answer` is `default`), or "cancelled".
    """
    qid = store.create(
        prompt=prompt,
        options=options,
        multi_select=multi_select,
        agent_id=agent_id,
        session_id=session_id,
        timeout_s=timeout_s,
        default_answer=default,
        priority=priority,
    )
    return _result(store.wait(qid))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

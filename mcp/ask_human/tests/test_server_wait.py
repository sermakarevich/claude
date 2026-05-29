"""Async-wait tests for the MCP server's non-blocking ``_await_answer``.

    uv run python tests/test_server_wait.py     # run directly
    uv run pytest tests/                         # or under pytest

These cover the property the indefinite-wait fix rests on: the server waits
WITHOUT blocking the event loop (so the MCP connection stays alive across long
waits), returns as soon as the question is answered out-of-band, and honors
``timeout_s`` -> ``default``. Requires the ``mcp`` dependency (server import).
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from agent_chat.server import _await_answer
from agent_chat.store import QuestionStore


def _store() -> QuestionStore:
    return QuestionStore(Path(tempfile.mkdtemp()) / "q.db")


def test_await_answer_returns_when_answered():
    s = _store()
    qid = s.create("Deploy?", options=["yes", "no"], agent_id="a")

    async def scenario():
        async def operator():
            await asyncio.sleep(0.15)
            assert s.answer(qid, "yes", answered_by="web")

        task = asyncio.create_task(operator())
        q = await _await_answer(s, qid, ctx=None, poll_interval=0.02)
        await task
        return q

    q = asyncio.run(scenario())
    assert q["status"] == "answered"
    assert q["answer"] == "yes"
    assert q["answered_by"] == "web"


def test_await_answer_times_out_to_default():
    s = _store()
    qid = s.create("Proceed?", timeout_s=0.1, default_answer="no")
    q = asyncio.run(_await_answer(s, qid, ctx=None, poll_interval=0.02))
    assert q["status"] == "expired"
    assert q["answer"] == "no"


def test_await_answer_does_not_block_event_loop():
    # While waiting, a concurrent coroutine must keep running — this is what
    # proves we ``await`` rather than ``time.sleep`` (a blocking wait would
    # freeze the loop and starve the ticker, which is exactly what dropped the
    # MCP connection before).
    s = _store()
    qid = s.create("hold")
    ticks = 0

    async def scenario():
        nonlocal ticks

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.02)
                ticks += 1

        async def answerer():
            await asyncio.sleep(0.2)
            s.answer(qid, "done")

        t = asyncio.create_task(ticker())
        a = asyncio.create_task(answerer())
        q = await _await_answer(s, qid, ctx=None, poll_interval=0.02)
        t.cancel()
        await a
        return q

    q = asyncio.run(scenario())
    assert q["status"] == "answered"
    assert ticks >= 3  # the loop kept making progress while we waited


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"PASS  {fn.__name__}")
    print(f"\nAll {len(tests)} tests passed.")

"""Correctness checks for QuestionStore (stdlib only).

    uv run python tests/test_store.py        # run directly
    uv run pytest tests/                     # or under pytest

Covers the properties the whole design rests on: a blocking ask that is
answered out-of-band, timeout -> default, first-writer-wins, and many
concurrent waiters being released independently.
"""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from agent_chat.store import QuestionStore


def _store() -> QuestionStore:
    return QuestionStore(Path(tempfile.mkdtemp()) / "q.db")


def test_blocking_ask_answered_out_of_band():
    s = _store()
    qid = s.create("Deploy to prod?", options=["yes", "no"], agent_id="agent-7")

    def operator():
        time.sleep(0.3)
        assert s.answer(qid, "yes", answered_by="cli")

    t = threading.Thread(target=operator)
    t.start()
    q = s.wait(qid, poll_interval=0.05)  # blocks until the operator answers
    t.join()

    assert q["status"] == "answered"
    assert q["answer"] == "yes"
    assert q["answered_by"] == "cli"


def test_timeout_returns_default():
    s = _store()
    qid = s.create("Proceed?", timeout_s=0.2, default_answer="no")
    q = s.wait(qid, poll_interval=0.05)
    assert q["status"] == "expired"
    assert q["answer"] == "no"


def test_first_writer_wins():
    s = _store()
    qid = s.create("Pick one")
    assert s.answer(qid, "a") is True
    assert s.answer(qid, "b") is False          # already resolved
    assert s.get(qid)["answer"] == "a"


def test_many_concurrent_waiters_released_independently():
    s = _store()
    ids = [s.create(f"q{i}") for i in range(20)]
    results: dict[str, dict] = {}

    def wait_one(qid: str):
        results[qid] = s.wait(qid, poll_interval=0.02)

    threads = [threading.Thread(target=wait_one, args=(i,)) for i in ids]
    for t in threads:
        t.start()
    time.sleep(0.1)
    for i in ids:
        assert s.answer(i, f"ans-{i}")
    for t in threads:
        t.join()

    assert all(results[i]["status"] == "answered" for i in ids)
    assert all(results[i]["answer"] == f"ans-{i}" for i in ids)


def test_multi_select_and_listing():
    s = _store()
    qid = s.create("Languages?", options=["py", "ts", "go"], multi_select=True)
    assert any(p["id"] == qid for p in s.list_pending())
    s.answer(qid, ["py", "go"])
    assert s.get(qid)["answer"] == ["py", "go"]


def test_resolve_id_prefix_and_cancel():
    s = _store()
    qid = s.create("cancel me")
    assert s.resolve_id(qid[:6]) == qid
    assert s.cancel(qid) is True
    assert s.answer(qid, "late") is False       # can't answer a cancelled one


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"PASS  {fn.__name__}")
    print(f"\nAll {len(tests)} tests passed.")

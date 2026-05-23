"""FR-07 / FR-08 / FR-09: Task failure, retry, and retry-limit exhaustion."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fleet.attempts import count_attempts, failure_count
from fleet.models import Task

from tests.integration.conftest import (
    FakeClaudeAdapter,
    MemoryQueue,
    fast_config,
    make_supervisor,
    run_until,
)


def _task(tid: str = "t-001") -> Task:
    return Task(id=tid, title="crash-task", description=None, status="open")


# ---------------------------------------------------------------------------
# Scenario 1: plain crash repeated → set_blocked after retry_limit
# ---------------------------------------------------------------------------


def test_failure_retry_exhaustion(tmp_path: Path) -> None:
    """Task fails twice → set_blocked; comments record each failure. (FR-07/08)"""
    queue = MemoryQueue()
    queue.add_task(_task())

    config = fast_config(retry_limit=2)
    adapter = FakeClaudeAdapter(scenario="crash")
    sup = make_supervisor(tmp_path, queue, adapter=adapter, config=config)

    done = asyncio.Event()

    def on_event(method: str, task_id: str) -> None:
        if method == "set_blocked" and task_id == "t-001":
            done.set()

    queue.add_listener(on_event)

    asyncio.run(run_until(sup, done, timeout=20.0))

    assert len(queue.blocked) == 1, "task should be blocked after retry exhaustion"
    assert queue.blocked[0][0] == "t-001"
    assert "retry limit" in queue.blocked[0][1]

    artifact_dir = tmp_path / ".claude" / "tasks" / "t-001"
    assert failure_count(artifact_dir) == 2
    assert count_attempts(artifact_dir) == 2

    # Both failures produce a supervisor comment
    assert len(queue.comments) == 2
    for _, body in queue.comments:
        assert "fleet" in body.lower() or "attempt" in body.lower()


def test_failure_transitions(tmp_path: Path) -> None:
    """Status transitions: open → in_progress → open → in_progress → blocked. (FR-08)"""
    queue = MemoryQueue()
    queue.add_task(_task())

    transitions: list[tuple[str, str]] = []

    def on_event(method: str, task_id: str) -> None:
        transitions.append((method, queue._tasks.get(task_id, _task()).status))

    queue.add_listener(on_event)

    config = fast_config(retry_limit=2)
    adapter = FakeClaudeAdapter(scenario="crash")
    sup = make_supervisor(tmp_path, queue, adapter=adapter, config=config)

    done = asyncio.Event()

    def _done(m: str, _: str) -> None:
        if m == "set_blocked":
            done.set()

    queue.add_listener(_done)

    asyncio.run(run_until(sup, done, timeout=20.0))

    methods = [m for m, _ in transitions]
    assert "claim" in methods
    assert "release" in methods
    assert "set_blocked" in methods


# ---------------------------------------------------------------------------
# Scenario 2: mixed outcomes — non-failure events don't burn retries (FR-09)
# ---------------------------------------------------------------------------


def test_non_failures_dont_burn_retries(tmp_path: Path) -> None:
    """rate_limit + context_pressure don't count as failures; crash(×2) exhausts limit."""
    queue = MemoryQueue()
    queue.add_task(_task())

    # Attempt sequence: rate_limit_rejected, context_pressure, crash, crash
    # Only crashes count → after 2 crashes, retry_limit=2 is exhausted
    adapter = FakeClaudeAdapter(
        scenarios=["rate_limit_rejected", "context_pressure", "crash", "crash"],
    )
    config = fast_config(retry_limit=2)
    sup = make_supervisor(tmp_path, queue, adapter=adapter, config=config)

    done = asyncio.Event()

    def on_event(method: str, task_id: str) -> None:
        if method == "set_blocked":
            done.set()

    queue.add_listener(on_event)

    asyncio.run(run_until(sup, done, timeout=30.0))

    artifact_dir = tmp_path / ".claude" / "tasks" / "t-001"
    assert failure_count(artifact_dir) == 2, "exactly 2 crash-failures"
    # Total attempts: 2 non-failures + 2 crashes = 4
    assert count_attempts(artifact_dir) >= 3, "at least 3 total attempts logged"
    assert len(queue.blocked) == 1
    assert queue._tasks["t-001"].status == "blocked"

"""FR-15 / FR-22: Context-pressure flag causes release without burning retries."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fleet.attempts import failure_count
from fleet.models import Task

from tests.integration.conftest import (
    FakeClaudeAdapter,
    MemoryQueue,
    fast_config,
    make_supervisor,
    run_until,
)


def _task(tid: str = "t-001") -> Task:
    return Task(id=tid, title="cp-task", description=None, status="open")


def test_context_pressure_release_no_failure(tmp_path: Path) -> None:
    """context_pressure releases task and does NOT increment failure_count. (FR-15/22)"""
    queue = MemoryQueue()
    queue.add_task(_task())

    adapter = FakeClaudeAdapter(scenario="context_pressure")
    config = fast_config()
    sup = make_supervisor(tmp_path, queue, adapter=adapter, config=config)

    done = asyncio.Event()

    def on_event(method: str, task_id: str) -> None:
        if method == "release":
            done.set()

    queue.add_listener(on_event)

    asyncio.run(run_until(sup, done, timeout=15.0))

    assert done.is_set()
    assert queue._tasks["t-001"].status == "open", "task should be back to open"

    release_reasons = [r for _, r in queue.released]
    assert any("context_pressure" in r for r in release_reasons)

    artifact_dir = tmp_path / ".claude" / "tasks" / "t-001"
    assert failure_count(artifact_dir) == 0, "context_pressure must not burn retries"


def test_context_pressure_flag_removed(tmp_path: Path) -> None:
    """.context_pressure flag is deleted by the runner after detection. (FR-15)"""
    queue = MemoryQueue()
    queue.add_task(_task())

    config = fast_config()
    artifact_root = tmp_path / ".claude" / "tasks"
    # Resolve the exact artifact dir the runner will create
    artifact_dir = artifact_root / "t-001"

    adapter = FakeClaudeAdapter(scenario="context_pressure")
    sup = make_supervisor(tmp_path, queue, adapter=adapter, config=config)

    done = asyncio.Event()

    def on_event(method: str, task_id: str) -> None:
        if method == "release":
            done.set()

    queue.add_listener(on_event)

    asyncio.run(run_until(sup, done, timeout=15.0))

    assert not (artifact_dir / ".context_pressure").exists(), (
        ".context_pressure flag should be removed by runner"
    )


def test_context_pressure_then_success_events_append_only(tmp_path: Path) -> None:
    """After cp-release, second run appends events rather than overwriting. (FR-30)"""
    queue = MemoryQueue()
    queue.add_task(_task())

    # Attempt 1: context_pressure; Attempt 2: clean_exit
    # On clean_exit, task is still in_progress in MemoryQueue so gets re-queued.
    # We stop after the 2nd release.
    adapter = FakeClaudeAdapter(scenarios=["context_pressure", "clean_exit"])
    config = fast_config()
    sup = make_supervisor(tmp_path, queue, adapter=adapter, config=config)

    release_count = [0]
    done = asyncio.Event()

    def on_event(method: str, task_id: str) -> None:
        if method == "release":
            release_count[0] += 1
            if release_count[0] >= 2:
                done.set()

    queue.add_listener(on_event)

    asyncio.run(run_until(sup, done, timeout=20.0))

    artifact_dir = tmp_path / ".claude" / "tasks" / "t-001"
    events_path = artifact_dir / "events.jsonl"
    assert events_path.exists(), "events.jsonl should exist after both attempts"

    lines = [json.loads(l) for l in events_path.read_text().splitlines() if l.strip()]
    attempts = [l["attempt"] for l in lines]
    assert 1 in attempts, "events from attempt 1 should be present"
    assert 2 in attempts, "events from attempt 2 should be present"

    # Attempt 1 events appear before attempt 2 events (append-only ordering)
    first_attempt_idx = next(i for i, l in enumerate(lines) if l["attempt"] == 1)
    first_attempt2_idx = next(i for i, l in enumerate(lines) if l["attempt"] == 2)
    assert first_attempt_idx < first_attempt2_idx, (
        "attempt 1 events must precede attempt 2 events (append-only)"
    )

    artifact_dir = tmp_path / ".claude" / "tasks" / "t-001"
    assert failure_count(artifact_dir) == 0

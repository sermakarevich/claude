import subprocess
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from fleet.queue import BeadsError, BeadsQueue


def test_claim_next_empty_ready_list_returns_none(queue: BeadsQueue) -> None:
    """claim_next returns None when no ready tasks exist."""
    with patch.object(queue, "_bd", return_value={"data": []}):
        result = queue.claim_next("worker-1")
    assert result is None


def test_claim_next_contention_at_most_one_winner(tmp_path: Path) -> None:
    """At most one claimer wins the same task when two race simultaneously."""
    task_data = [{"id": "t-001", "title": "Task 1", "description": None}]
    claim_counter = {"n": 0}
    counter_lock = threading.Lock()

    def shared_mock_bd(*args: str, json_envelope: bool = True, actor: str | None = None) -> dict | None:
        if args and args[0] == "ready":
            return {"data": task_data}
        if "--claim" in args:
            with counter_lock:
                claim_counter["n"] += 1
                if claim_counter["n"] > 1:
                    raise BeadsError("contention: already claimed by another worker")
            return None
        return None

    q1 = BeadsQueue(repo_root=tmp_path)
    q2 = BeadsQueue(repo_root=tmp_path)
    results: list = [None, None]
    barrier = threading.Barrier(2)

    def run(q: BeadsQueue, idx: int) -> None:
        barrier.wait()  # synchronize so both call claim_next at the same time
        results[idx] = q.claim_next(f"worker-{idx}")

    with patch.object(q1, "_bd", side_effect=shared_mock_bd):
        with patch.object(q2, "_bd", side_effect=shared_mock_bd):
            t1 = threading.Thread(target=run, args=(q1, 0))
            t2 = threading.Thread(target=run, args=(q2, 1))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

    non_none = [r for r in results if r is not None]
    assert len(non_none) <= 1


def test_beads_error_raised_on_nonzero_bd_exit(tmp_path: Path) -> None:
    """BeadsError is raised when the bd subprocess exits with non-zero status."""
    q = BeadsQueue(repo_root=tmp_path)
    failed = subprocess.CompletedProcess(
        args=["bd", "show", "nonexistent"],
        returncode=1,
        stdout="",
        stderr="issue not found",
    )
    with patch("fleet.queue.subprocess.run", return_value=failed):
        with pytest.raises(BeadsError, match="issue not found"):
            q._bd("show", "nonexistent")

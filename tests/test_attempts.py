from pathlib import Path

import pytest

from fleet.attempts import count_attempts


def test_returns_zero_when_no_attempts_dir(tmp_path: Path):
    assert count_attempts(tmp_path, "t-001") == 0


def test_returns_zero_when_attempts_dir_empty(tmp_path: Path):
    (tmp_path / "attempts").mkdir()
    assert count_attempts(tmp_path, "t-001") == 0


def test_counts_jsonl_files(tmp_path: Path):
    attempts_dir = tmp_path / "attempts"
    attempts_dir.mkdir()
    (attempts_dir / "t-001-attempt-1-2026-05-23.jsonl").touch()
    (attempts_dir / "t-001-attempt-2-2026-05-24.jsonl").touch()
    assert count_attempts(tmp_path, "t-001") == 2


def test_isolates_per_task_counts(tmp_path: Path):
    attempts_dir = tmp_path / "attempts"
    attempts_dir.mkdir()
    (attempts_dir / "t-001-attempt-1-2026-05-23.jsonl").touch()
    (attempts_dir / "t-002-attempt-1-2026-05-23.jsonl").touch()
    (attempts_dir / "t-002-attempt-2-2026-05-24.jsonl").touch()
    assert count_attempts(tmp_path, "t-001") == 1
    assert count_attempts(tmp_path, "t-002") == 2


def test_does_not_count_stderr_files(tmp_path: Path):
    attempts_dir = tmp_path / "attempts"
    attempts_dir.mkdir()
    (attempts_dir / "t-001-attempt-1-2026-05-23.jsonl").touch()
    (attempts_dir / "t-001-attempt-1-2026-05-23.stderr").touch()
    assert count_attempts(tmp_path, "t-001") == 1

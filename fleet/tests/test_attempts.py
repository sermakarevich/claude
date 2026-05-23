from pathlib import Path

from fleet.attempts import count_attempts, failure_count, increment_failure


def test_returns_zero_when_artifact_dir_missing(tmp_path: Path):
    assert count_attempts(tmp_path / "missing") == 0


def test_returns_zero_when_artifact_dir_empty(tmp_path: Path):
    artifact_dir = tmp_path / "t-001"
    artifact_dir.mkdir()
    assert count_attempts(artifact_dir) == 0


def test_counts_jsonl_files(tmp_path: Path):
    artifact_dir = tmp_path / "t-001"
    artifact_dir.mkdir()
    (artifact_dir / "attempt-1-2026-05-23.jsonl").touch()
    (artifact_dir / "attempt-2-2026-05-24.jsonl").touch()
    assert count_attempts(artifact_dir) == 2


def test_isolates_per_task_counts(tmp_path: Path):
    dir1 = tmp_path / "t-001"
    dir2 = tmp_path / "t-002"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "attempt-1-2026-05-23.jsonl").touch()
    (dir2 / "attempt-1-2026-05-23.jsonl").touch()
    (dir2 / "attempt-2-2026-05-24.jsonl").touch()
    assert count_attempts(dir1) == 1
    assert count_attempts(dir2) == 2


def test_does_not_count_stderr_files(tmp_path: Path):
    artifact_dir = tmp_path / "t-001"
    artifact_dir.mkdir()
    (artifact_dir / "attempt-1-2026-05-23.jsonl").touch()
    (artifact_dir / "attempt-1-2026-05-23.stderr").touch()
    assert count_attempts(artifact_dir) == 1


def test_failure_count_zero_when_missing(tmp_path: Path):
    assert failure_count(tmp_path / "t-001") == 0


def test_increment_failure_creates_and_increments(tmp_path: Path):
    artifact_dir = tmp_path / "t-001"
    assert increment_failure(artifact_dir) == 1
    assert increment_failure(artifact_dir) == 2
    assert failure_count(artifact_dir) == 2

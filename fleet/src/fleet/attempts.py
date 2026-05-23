from pathlib import Path


def count_attempts(artifact_dir: Path) -> int:
    """Count per-attempt JSONL files in the task's artifact directory."""
    if not artifact_dir.exists():
        return 0
    return len(list(artifact_dir.glob("attempt-*-*.jsonl")))


def failure_count(artifact_dir: Path) -> int:
    """Return the number of FAILURE outcomes recorded for this task."""
    count_file = artifact_dir / "failures.count"
    if not count_file.exists():
        return 0
    try:
        return int(count_file.read_text().strip())
    except (ValueError, OSError):
        return 0


def increment_failure(artifact_dir: Path) -> int:
    """Increment the failure counter for this task and return the new count."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    new_count = failure_count(artifact_dir) + 1
    (artifact_dir / "failures.count").write_text(str(new_count))
    return new_count

from pathlib import Path


def count_attempts(log_root: Path, task_id: str) -> int:
    """Count existing per-attempt JSONL files for task_id."""
    attempts_dir = log_root / "attempts"
    if not attempts_dir.exists():
        return 0
    return len(list(attempts_dir.glob(f"{task_id}-attempt-*-*.jsonl")))


def failure_count(log_root: Path, task_id: str) -> int:
    """Return the number of FAILURE outcomes recorded for task_id."""
    count_file = log_root / "attempts" / f"{task_id}-failures.count"
    if not count_file.exists():
        return 0
    try:
        return int(count_file.read_text().strip())
    except (ValueError, OSError):
        return 0


def increment_failure(log_root: Path, task_id: str) -> int:
    """Increment the failure counter for task_id and return the new count."""
    attempts_dir = log_root / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    current = failure_count(log_root, task_id)
    new_count = current + 1
    count_file = attempts_dir / f"{task_id}-failures.count"
    count_file.write_text(str(new_count))
    return new_count

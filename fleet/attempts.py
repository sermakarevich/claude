from pathlib import Path


def count_attempts(log_root: Path, task_id: str) -> int:
    """Count existing per-attempt JSONL files for task_id."""
    attempts_dir = log_root / "attempts"
    if not attempts_dir.exists():
        return 0
    return len(list(attempts_dir.glob(f"{task_id}-attempt-*-*.jsonl")))

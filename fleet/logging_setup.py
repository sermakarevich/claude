from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import IO

import structlog

from fleet.events import Event
from fleet.redact import redact

_PROCESSORS: list = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.add_log_level,
    structlog.processors.JSONRenderer(),
]


class _TeeStream:
    """Write-proxy that fans writes to multiple text streams."""

    def __init__(self, *streams: IO[str]) -> None:
        self._streams = streams

    def write(self, msg: str) -> int:
        for s in self._streams:
            s.write(msg)
        return len(msg)

    def flush(self) -> None:
        for s in self._streams:
            s.flush()


class AttemptLog:
    def __init__(
        self,
        log: structlog.BoundLogger,
        event_path: Path | None,
        stderr_file: IO[bytes],
        _jsonl_file: IO[str],
    ) -> None:
        self.log = log
        self.event_path = event_path
        self.stderr_file = stderr_file
        self._jsonl_file = _jsonl_file

    def __enter__(self) -> AttemptLog:
        return self

    def __exit__(self, *_) -> None:
        self._jsonl_file.flush()
        self._jsonl_file.close()
        self.stderr_file.flush()
        self.stderr_file.close()


def setup_supervisor_logger(log_root: Path) -> structlog.BoundLogger:
    """Configure structlog globally and return a supervisor BoundLogger.

    Sinks to <log_root>/fleet-<date>.jsonl (append) and stderr.
    """
    log_root.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    fleet_path = log_root / f"fleet-{date}.jsonl"
    fleet_file = fleet_path.open("a", encoding="utf-8")
    tee = _TeeStream(fleet_file, sys.stderr)
    structlog.configure(
        processors=_PROCESSORS,
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=tee),
    )
    return structlog.get_logger().bind(component="supervisor", pid=os.getpid())


def open_attempt_log(log_root: Path, task_id: str, attempt: int) -> AttemptLog:
    """Open per-attempt JSONL and stderr files; return an AttemptLog context manager."""
    attempts_dir = log_root / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    stem = f"{task_id}-attempt-{attempt}-{date}"
    jsonl_path = attempts_dir / f"{stem}.jsonl"
    stderr_path = attempts_dir / f"{stem}.stderr"
    jsonl_file = jsonl_path.open("a", encoding="utf-8")
    stderr_file = stderr_path.open("ab", buffering=0)
    log = structlog.wrap_logger(
        structlog.PrintLogger(jsonl_file),
        processors=_PROCESSORS,
    ).bind(task_id=task_id, attempt=attempt, pid=os.getpid())
    return AttemptLog(
        log=log,
        event_path=None,
        stderr_file=stderr_file,
        _jsonl_file=jsonl_file,
    )


def append_event(artifact_dir: Path, evt: Event, attempt: int) -> None:
    """Append one normalized Event line to <artifact_dir>/events.jsonl.

    Never truncates prior content (append mode, line-flushed).
    Redacts credentials before serialising.
    """
    payload: dict = {
        "kind": evt.kind,
        "ts": evt.ts.isoformat(),
        "attempt": attempt,
        "session_id": evt.session_id,
        "tool_name": evt.tool_name,
        "usage": evt.usage,
        "rate_info": evt.rate_info,
        "raw": evt.raw,
    }
    payload = redact(payload)
    events_path = artifact_dir / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
        f.flush()

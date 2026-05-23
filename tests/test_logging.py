import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import structlog

from fleet.events import Event
from fleet.logging_setup import AttemptLog, append_event, open_attempt_log, setup_supervisor_logger


@pytest.fixture(autouse=True)
def reset_structlog():
    yield
    structlog.reset_defaults()


def _ts() -> datetime:
    return datetime.now(tz=timezone.utc)


def test_setup_supervisor_logger_writes_jsonl(tmp_path: Path):
    log = setup_supervisor_logger(tmp_path)
    log.info("test_event", foo="bar")

    date = datetime.now().strftime("%Y-%m-%d")
    fleet_path = tmp_path / f"fleet-{date}.jsonl"
    assert fleet_path.exists()

    lines = fleet_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "test_event"
    assert record["foo"] == "bar"
    assert "timestamp" in record
    assert record["level"] == "info"


def test_setup_supervisor_logger_binds_supervisor_context(tmp_path: Path):
    log = setup_supervisor_logger(tmp_path)
    log.info("ping")

    date = datetime.now().strftime("%Y-%m-%d")
    fleet_path = tmp_path / f"fleet-{date}.jsonl"
    record = json.loads(fleet_path.read_text().strip())
    assert record["component"] == "supervisor"
    assert "pid" in record


def test_open_attempt_log_creates_jsonl_and_stderr_files(tmp_path: Path):
    date = datetime.now().strftime("%Y-%m-%d")
    with open_attempt_log(tmp_path, "t-001", 1) as al:
        al.log.info("subprocess_started")

    stem = f"t-001-attempt-1-{date}"
    jsonl_path = tmp_path / "attempts" / f"{stem}.jsonl"
    stderr_path = tmp_path / "attempts" / f"{stem}.stderr"
    assert jsonl_path.exists()
    assert stderr_path.exists()


def test_open_attempt_log_jsonl_contains_bound_fields(tmp_path: Path):
    date = datetime.now().strftime("%Y-%m-%d")
    with open_attempt_log(tmp_path, "t-001", 2) as al:
        al.log.info("subprocess_started")

    jsonl_path = tmp_path / "attempts" / f"t-001-attempt-2-{date}.jsonl"
    record = json.loads(jsonl_path.read_text().strip())
    assert record["event"] == "subprocess_started"
    assert record["task_id"] == "t-001"
    assert record["attempt"] == 2
    assert "pid" in record


def test_open_attempt_log_returns_attempt_log_instance(tmp_path: Path):
    al = open_attempt_log(tmp_path, "t-001", 1)
    assert isinstance(al, AttemptLog)
    assert hasattr(al, "log")
    assert hasattr(al, "event_path")
    assert hasattr(al, "stderr_file")
    al.__exit__(None, None, None)


def test_append_event_writes_one_json_line(tmp_path: Path):
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    evt = Event(kind="result", raw={"x": 1}, ts=_ts(), session_id="sess-1")
    append_event(artifact_dir, evt, attempt=1)

    events_path = artifact_dir / "events.jsonl"
    assert events_path.exists()
    record = json.loads(events_path.read_text().strip())
    assert record["kind"] == "result"
    assert record["attempt"] == 1
    assert record["session_id"] == "sess-1"
    assert record["raw"] == {"x": 1}


def test_append_event_never_truncates_prior_content(tmp_path: Path):
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    ts = _ts()
    evt1 = Event(kind="result", raw={}, ts=ts, session_id="sess-a")
    evt2 = Event(kind="error", raw={}, ts=ts, session_id="sess-b")
    append_event(artifact_dir, evt1, attempt=1)
    append_event(artifact_dir, evt2, attempt=2)

    lines = (artifact_dir / "events.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["kind"] == "result"
    assert json.loads(lines[1])["kind"] == "error"


def test_append_event_redacts_credentials(tmp_path: Path):
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    evt = Event(
        kind="result",
        raw={"ANTHROPIC_API_KEY": "sk-secret-123", "safe": "value"},
        ts=_ts(),
    )
    append_event(artifact_dir, evt, attempt=1)

    record = json.loads((artifact_dir / "events.jsonl").read_text().strip())
    assert record["raw"]["ANTHROPIC_API_KEY"] == "<redacted>"
    assert record["raw"]["safe"] == "value"

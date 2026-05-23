"""Tests for the `fleet` CLI surface (FR-32)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from fleet.cli import app
from fleet.models import Task
from fleet.queue import BeadsError

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help output (FR-32)
# ---------------------------------------------------------------------------


def test_help_lists_required_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in (
        "create",
        "ready",
        "show",
        "release",
        "close",
        "run",
        "config",
        "tasks",
        "task",
    ):
        assert cmd in result.output, f"Expected '{cmd}' in fleet --help output"


def test_help_does_not_list_forbidden_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "block" not in result.output
    assert "answer" not in result.output


def test_config_help_lists_show_and_set() -> None:
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "set" in result.output


# ---------------------------------------------------------------------------
# fleet show
# ---------------------------------------------------------------------------


def test_show_missing_task_exits_nonzero() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.get.side_effect = BeadsError("task not found: missing-task")
        result = runner.invoke(app, ["show", "missing-task"])
    assert result.exit_code != 0


def test_show_missing_task_prints_error_message() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.get.side_effect = BeadsError("task not found: missing-task")
        result = runner.invoke(app, ["show", "missing-task"])
    assert "missing-task" in result.stderr or "not found" in result.stderr


def test_show_existing_task_prints_fields() -> None:
    task = Task(id="t-001", title="My task", description="A desc", status="open")
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.get.return_value = task
        result = runner.invoke(app, ["show", "t-001"])
    assert result.exit_code == 0
    assert "t-001" in result.output
    assert "My task" in result.output


# ---------------------------------------------------------------------------
# fleet run
# ---------------------------------------------------------------------------


def test_run_unknown_adapter_exits_nonzero() -> None:
    result = runner.invoke(app, ["run", "--adapter", "does-not-exist"])
    assert result.exit_code != 0


def test_run_unknown_adapter_lists_available_adapters() -> None:
    result = runner.invoke(app, ["run", "--adapter", "does-not-exist"])
    combined = result.output + result.stderr
    assert "Available" in combined or "claude" in combined


def test_run_missing_adapter_flag_exits_nonzero() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0


def test_run_once_known_adapter_exits_zero() -> None:
    """fleet run --adapter claude --once runs through supervisor and exits 0."""
    with patch("fleet.cli.BeadsQueue"):
        with patch("fleet.cli.Supervisor") as mock_cls:
            mock_sup = MagicMock()
            mock_sup.run = AsyncMock(return_value=0)
            mock_cls.return_value = mock_sup
            result = runner.invoke(app, ["run", "--adapter", "claude", "--once"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# fleet ready / release / close (smoke tests)
# ---------------------------------------------------------------------------


def test_ready_no_tasks_prints_message() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.list_ready.return_value = []
        result = runner.invoke(app, ["ready"])
    assert result.exit_code == 0
    assert "No ready tasks" in result.output


def test_release_calls_queue_release() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        result = runner.invoke(app, ["release", "t-001", "--reason", "testing"])
    assert result.exit_code == 0
    mock_q.release.assert_called_once_with("t-001", reason="testing")


def test_close_calls_queue_close() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        result = runner.invoke(app, ["close", "t-001"])
    assert result.exit_code == 0
    mock_q.close.assert_called_once_with("t-001", reason="completed")


# ---------------------------------------------------------------------------
# fleet prompt
# ---------------------------------------------------------------------------


def test_prompt_claude_writes_template_to_pwd(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["prompt", "claude"])
    assert result.exit_code == 0, result.output + (result.stderr or "")
    dest = tmp_path / ".claude" / "CLAUDE.md"
    assert dest.exists()
    assert "fleet" in dest.read_text().lower()


def test_prompt_claude_refuses_existing_without_force(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".claude" / "CLAUDE.md"
    dest.parent.mkdir()
    dest.write_text("existing content", encoding="utf-8")

    result = runner.invoke(app, ["prompt", "claude"])
    assert result.exit_code != 0
    assert dest.read_text() == "existing content"
    assert "already exists" in (result.stderr or result.output)


def test_prompt_claude_overwrites_with_force(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".claude" / "CLAUDE.md"
    dest.parent.mkdir()
    dest.write_text("existing content", encoding="utf-8")

    result = runner.invoke(app, ["prompt", "claude", "--force"])
    assert result.exit_code == 0
    assert dest.read_text() != "existing content"


def test_prompt_claude_dest_override(tmp_path) -> None:
    dest = tmp_path / "custom" / "INSTRUCTIONS.md"
    result = runner.invoke(app, ["prompt", "claude", "--dest", str(dest)])
    assert result.exit_code == 0
    assert dest.exists()


def test_prompt_agents_default_dest(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["prompt", "agents"])
    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# fleet bd (passthrough)
# ---------------------------------------------------------------------------


def test_bd_passthrough_forwards_args_with_fleet_home_cwd(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    completed = MagicMock(returncode=0)
    with patch("fleet.cli.subprocess.run", return_value=completed) as mock_run:
        result = runner.invoke(app, ["bd", "ready", "--limit", "5", "--json"])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == ["bd", "ready", "--limit", "5", "--json"]
    assert kwargs["cwd"] == Path(tmp_path).resolve()


def test_bd_passthrough_propagates_nonzero_exit_code(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    completed = MagicMock(returncode=2)
    with patch("fleet.cli.subprocess.run", return_value=completed):
        result = runner.invoke(app, ["bd", "show", "missing-id"])
    assert result.exit_code == 2


def test_bd_passthrough_does_not_intercept_help_flag(tmp_path, monkeypatch) -> None:
    """A `--help` after `bd` should be passed to bd, not handled by typer."""
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    completed = MagicMock(returncode=0)
    with patch("fleet.cli.subprocess.run", return_value=completed) as mock_run:
        runner.invoke(app, ["bd", "--help"])
    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["bd", "--help"]


def test_bd_passthrough_listed_in_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bd" in result.output


# ---------------------------------------------------------------------------
# fleet log
# ---------------------------------------------------------------------------


def _seed_log_dir(home: Path, filename: str, content: str) -> Path:
    log_dir = home / "logging"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_log_prints_full_file_when_no_argument(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    body = "line1\nline2\nline3\n"
    _seed_log_dir(tmp_path, "fleet-2026-05-23.jsonl", body)

    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0, result.output + (result.stderr or "")
    assert result.output == body


def test_log_tails_last_n_lines(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    body = "".join(f"line{i}\n" for i in range(1, 11))
    _seed_log_dir(tmp_path, "fleet-2026-05-23.jsonl", body)

    result = runner.invoke(app, ["log", "3"])
    assert result.exit_code == 0, result.output + (result.stderr or "")
    assert result.output == "line8\nline9\nline10\n"


def test_log_picks_most_recent_file(tmp_path, monkeypatch) -> None:
    import os
    import time

    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    older = _seed_log_dir(tmp_path, "fleet-2026-05-22.jsonl", "old\n")
    time.sleep(0.01)
    newer = _seed_log_dir(tmp_path, "fleet-2026-05-23.jsonl", "new\n")
    # Force older mtime to be earlier in case the FS coarse-grains it.
    os.utime(older, (older.stat().st_atime, newer.stat().st_mtime - 1))

    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0
    assert result.output == "new\n"


def test_log_errors_when_no_log_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    result = runner.invoke(app, ["log"])
    assert result.exit_code != 0
    assert "No log" in (result.stderr or result.output)


def test_log_errors_when_log_dir_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    (tmp_path / "logging").mkdir()
    result = runner.invoke(app, ["log"])
    assert result.exit_code != 0
    assert "No log files" in (result.stderr or result.output)


def test_log_rejects_non_positive_tail(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    _seed_log_dir(tmp_path, "fleet-2026-05-23.jsonl", "x\n")
    result = runner.invoke(app, ["log", "0"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# fleet tasks / fleet task <id> <action>
# ---------------------------------------------------------------------------


def test_tasks_no_running_prints_message() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.list_in_progress.return_value = []
        result = runner.invoke(app, ["tasks"])
    assert result.exit_code == 0
    assert "No running tasks" in result.output


def test_tasks_lists_in_progress_tasks() -> None:
    tasks = [
        Task(id="t-001", title="First", description=None, status="in_progress"),
        Task(id="t-002", title="Second", description=None, status="in_progress", cwd="/x"),
    ]
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.list_in_progress.return_value = tasks
        result = runner.invoke(app, ["tasks"])
    assert result.exit_code == 0
    assert "t-001" in result.output
    assert "First" in result.output
    assert "t-002" in result.output
    assert "Second" in result.output
    assert "/x" in result.output


def test_tasks_beads_error_exits_nonzero() -> None:
    with patch("fleet.cli.BeadsQueue") as mock_cls:
        mock_q = MagicMock()
        mock_cls.return_value = mock_q
        mock_q.list_in_progress.side_effect = BeadsError("bd boom")
        result = runner.invoke(app, ["tasks"])
    assert result.exit_code != 0
    assert "bd boom" in (result.stderr or result.output)


def _seed_task_dir(home: Path, task_id: str) -> Path:
    task_dir = home / "tasks" / task_id
    (task_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (task_dir / "attempts").mkdir(parents=True, exist_ok=True)
    return task_dir


def test_task_plan_prints_plan_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    task_dir = _seed_task_dir(tmp_path, "t-001")
    body = "# t-001 — PLAN_AND_STATUS\n\nstuff\n"
    (task_dir / "artifacts" / "PLAN_AND_STATUS.md").write_text(body, encoding="utf-8")

    result = runner.invoke(app, ["task", "t-001", "plan"])
    assert result.exit_code == 0, result.output + (result.stderr or "")
    assert result.output == body


def test_task_knowledge_prints_knowledge_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    task_dir = _seed_task_dir(tmp_path, "t-001")
    body = "# t-001 — KNOWLEDGE\n\nthings\n"
    (task_dir / "artifacts" / "KNOWLEDGE.md").write_text(body, encoding="utf-8")

    result = runner.invoke(app, ["task", "t-001", "knowledge"])
    assert result.exit_code == 0, result.output + (result.stderr or "")
    assert result.output == body


def test_task_log_prints_latest_attempt(tmp_path, monkeypatch) -> None:
    import os
    import time

    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    task_dir = _seed_task_dir(tmp_path, "t-001")
    older = task_dir / "attempts" / "attempt-1-2026-05-22.jsonl"
    newer = task_dir / "attempts" / "attempt-2-2026-05-23.jsonl"
    older.write_text("old\n", encoding="utf-8")
    time.sleep(0.01)
    newer.write_text("new\n", encoding="utf-8")
    os.utime(older, (older.stat().st_atime, newer.stat().st_mtime - 1))

    result = runner.invoke(app, ["task", "t-001", "log"])
    assert result.exit_code == 0
    assert result.output == "new\n"


def test_task_missing_task_dir_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    result = runner.invoke(app, ["task", "t-missing", "plan"])
    assert result.exit_code != 0
    assert "No task directory" in (result.stderr or result.output)


def test_task_plan_missing_file_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    _seed_task_dir(tmp_path, "t-001")
    result = runner.invoke(app, ["task", "t-001", "plan"])
    assert result.exit_code != 0
    assert "PLAN_AND_STATUS" in (result.stderr or result.output)


def test_task_log_no_attempts_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    _seed_task_dir(tmp_path, "t-001")
    result = runner.invoke(app, ["task", "t-001", "log"])
    assert result.exit_code != 0
    assert "No attempt logs" in (result.stderr or result.output)


def test_task_invalid_action_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLEET_HOME", str(tmp_path))
    _seed_task_dir(tmp_path, "t-001")
    result = runner.invoke(app, ["task", "t-001", "bogus"])
    assert result.exit_code != 0

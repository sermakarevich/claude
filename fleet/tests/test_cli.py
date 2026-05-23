"""Tests for the `fleet` CLI surface (FR-32)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from fleet.cli import app
from fleet.models import Task
from fleet.queue import BeadsError

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Help output (FR-32)
# ---------------------------------------------------------------------------


def test_help_lists_required_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("create", "ready", "show", "release", "close", "run", "config"):
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

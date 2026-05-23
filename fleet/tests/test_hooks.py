"""Tests for fleet hook scripts (test-after)."""
import os
import subprocess
from pathlib import Path

HOOKS_DIR = Path(__file__).parent.parent / "fleet" / "hooks"
PRECOMPACT = HOOKS_DIR / "precompact.sh"
PRETOOL = HOOKS_DIR / "pretool_askuserquestion.sh"


def _run(script: Path, env_override: dict | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "FLEET_ARTIFACT_DIR"}
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["sh", str(script)],
        capture_output=True,
        text=True,
        env=env,
    )


class TestPrecompact:
    def test_with_artifact_dir_creates_flag_and_exits_2(self, tmp_path):
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()
        result = _run(PRECOMPACT, {"FLEET_ARTIFACT_DIR": str(artifact_dir)})
        assert result.returncode == 2
        assert (artifact_dir / ".context_pressure").exists()

    def test_without_artifact_dir_writes_stderr_and_exits_0(self):
        result = _run(PRECOMPACT)
        assert result.returncode == 0
        assert result.stderr.strip() != ""

    def test_with_artifact_dir_empty_string_writes_stderr_and_exits_0(self):
        result = _run(PRECOMPACT, {"FLEET_ARTIFACT_DIR": ""})
        assert result.returncode == 0
        assert result.stderr.strip() != ""


class TestPretoolAskUserQuestion:
    def test_always_exits_2(self):
        result = _run(PRETOOL)
        assert result.returncode == 2

    def test_emits_corrective_message_to_stderr(self):
        result = _run(PRETOOL)
        assert "AskUserQuestion is not available in headless fleet mode" in result.stderr
        assert "bd update" in result.stderr
        assert "Q&A.md" in result.stderr
        assert result.stdout == ""

    def test_no_stdout(self):
        result = _run(PRETOOL)
        assert result.stdout == ""

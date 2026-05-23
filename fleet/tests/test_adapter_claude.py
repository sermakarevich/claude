import json
from pathlib import Path

import pytest

from fleet.adapter import CoderAdapter
from fleet.adapters import get_adapter
from fleet.adapters.claude_cli import ClaudeCLIAdapter
from fleet.models import Task


FIXTURES = Path(__file__).parent / "fixtures"


def _adapter() -> ClaudeCLIAdapter:
    return ClaudeCLIAdapter()


def _task(task_id: str = "test-001") -> Task:
    return Task(id=task_id, title="Test task", description="Do the thing.", status="in_progress")


def _lines(fixture: str) -> list[str]:
    return [
        line for line in (FIXTURES / fixture).read_text().splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_get_adapter_returns_claude_class():
    cls = get_adapter("claude")
    assert cls is ClaudeCLIAdapter


def test_get_adapter_unknown_raises():
    with pytest.raises(ValueError, match="Unknown adapter"):
        get_adapter("unknown_cli")


def test_claude_adapter_is_subclass_of_coder_adapter():
    assert issubclass(ClaudeCLIAdapter, CoderAdapter)


# ---------------------------------------------------------------------------
# build_argv — FR-10
# ---------------------------------------------------------------------------

def test_build_argv_starts_with_claude_p(tmp_path: Path):
    adapter = _adapter()
    task = _task()
    argv = adapter.build_argv(task, tmp_path)
    assert argv[0] == "claude"
    assert "-p" in argv


def test_build_argv_includes_stream_json_output(tmp_path: Path):
    adapter = _adapter()
    argv = adapter.build_argv(_task(), tmp_path)
    idx = argv.index("--output-format")
    assert argv[idx + 1] == "stream-json"


def test_build_argv_includes_task_id_in_prompt(tmp_path: Path):
    adapter = _adapter()
    task = _task("my-task-id")
    argv = adapter.build_argv(task, tmp_path)
    prompt = " ".join(argv)
    assert "my-task-id" in prompt


# ---------------------------------------------------------------------------
# env
# ---------------------------------------------------------------------------

def test_env_includes_required_vars(tmp_path: Path):
    adapter = _adapter()
    task = _task("t-42")
    env = adapter.env(task, tmp_path, attempt=2)
    assert env["FLEET_TASK_ID"] == "t-42"
    assert env["FLEET_ARTIFACT_DIR"] == str(tmp_path)
    assert env["FLEET_ATTEMPT"] == "2"


def test_env_does_not_contain_api_key(tmp_path: Path):
    adapter = _adapter()
    env = adapter.env(_task(), tmp_path, attempt=0)
    assert "ANTHROPIC_API_KEY" not in env


# ---------------------------------------------------------------------------
# normalize_event — malformed input
# ---------------------------------------------------------------------------

def test_normalize_event_returns_none_for_malformed_json():
    adapter = _adapter()
    assert adapter.normalize_event("not json") is None
    assert adapter.normalize_event("") is None
    assert adapter.normalize_event("{bad") is None


def test_normalize_event_returns_none_for_non_dict():
    adapter = _adapter()
    assert adapter.normalize_event("[1,2,3]") is None


def test_normalize_event_returns_none_for_unknown_type():
    adapter = _adapter()
    assert adapter.normalize_event('{"type": "completely_unknown_type"}') is None


# ---------------------------------------------------------------------------
# normalize_event — assistant_text
# ---------------------------------------------------------------------------

def test_normalize_assistant_text():
    adapter = _adapter()
    [line] = _lines("claude_stream_basic.jsonl")[:1]
    evt = adapter.normalize_event(line)
    assert evt is not None
    assert evt.kind == "assistant_text"
    assert evt.session_id == "sess_abc123"
    assert evt.usage is not None
    assert evt.usage["input_tokens"] == 100


# ---------------------------------------------------------------------------
# normalize_event — tool_use
# ---------------------------------------------------------------------------

def test_normalize_tool_use():
    adapter = _adapter()
    lines = _lines("claude_stream_basic.jsonl")
    # second line is tool_use
    evt = adapter.normalize_event(lines[1])
    assert evt is not None
    assert evt.kind == "tool_use"
    assert evt.tool_name == "Read"


# ---------------------------------------------------------------------------
# normalize_event — tool_result
# ---------------------------------------------------------------------------

def test_normalize_tool_result():
    adapter = _adapter()
    lines = _lines("claude_stream_basic.jsonl")
    # third line is tool_result
    evt = adapter.normalize_event(lines[2])
    assert evt is not None
    assert evt.kind == "tool_result"
    assert evt.tool_name == "Read"


# ---------------------------------------------------------------------------
# normalize_event — session_started / session_ended
# ---------------------------------------------------------------------------

def test_normalize_session_started():
    adapter = _adapter()
    [init_line, _result_line] = _lines("claude_stream_session.jsonl")
    evt = adapter.normalize_event(init_line)
    assert evt is not None
    assert evt.kind == "session_started"
    assert evt.session_id == "sess_xyz789"


def test_normalize_session_ended():
    adapter = _adapter()
    [_init_line, result_line] = _lines("claude_stream_session.jsonl")
    evt = adapter.normalize_event(result_line)
    assert evt is not None
    assert evt.kind == "session_ended"
    assert evt.session_id == "sess_xyz789"
    assert evt.usage is not None
    assert evt.usage["input_tokens"] == 2500


# ---------------------------------------------------------------------------
# normalize_event — rate_limit_info (FR-19 soft path)
# ---------------------------------------------------------------------------

def test_normalize_rate_limit_info():
    adapter = _adapter()
    [line] = _lines("claude_stream_rate_limit_info.jsonl")
    evt = adapter.normalize_event(line)
    assert evt is not None
    assert evt.kind == "rate_limit_info"
    assert evt.rate_info is not None
    assert evt.rate_info["usage_pct"] == pytest.approx(85.5)
    assert evt.rate_info["resets_at"] == 1748001000
    assert evt.rate_info["status"] == "approaching"


# ---------------------------------------------------------------------------
# normalize_event — rate_limit (FR-19 hard rejection)
# ---------------------------------------------------------------------------

def test_normalize_rate_limit_rejected():
    adapter = _adapter()
    [line] = _lines("claude_stream_rate_limit_rejected.jsonl")
    evt = adapter.normalize_event(line)
    assert evt is not None
    assert evt.kind == "rate_limit"
    assert evt.rate_info is not None
    assert evt.rate_info["status"] == "rejected"
    assert evt.rate_info["resets_at"] == 1748001600


# ---------------------------------------------------------------------------
# normalize_event — thinking blocks
# ---------------------------------------------------------------------------

def test_normalize_thinking_event():
    adapter = _adapter()
    raw = json.dumps({
        "type": "assistant",
        "message": {
            "content": [{"type": "thinking", "thinking": "Let me reason..."}],
            "usage": {"input_tokens": 50, "output_tokens": 30},
        },
        "session_id": "sess_think",
    })
    evt = adapter.normalize_event(raw)
    assert evt is not None
    assert evt.kind == "thinking"
    assert evt.session_id == "sess_think"


# ---------------------------------------------------------------------------
# write_runtime_config is implemented (Task 4)
# ---------------------------------------------------------------------------

def test_write_runtime_config_runs_without_error(tmp_path: Path):
    adapter = _adapter()
    adapter.write_runtime_config(tmp_path, {})
    assert (tmp_path / ".claude" / "settings.json").exists()


# ---------------------------------------------------------------------------
# No anthropic / claude-agent-sdk imports in adapter files (FR-33, FR-35)
# ---------------------------------------------------------------------------

def test_no_anthropic_import_in_adapter_module():
    import fleet.adapter as adapter_mod
    import fleet.adapters.claude_cli as cli_mod
    import fleet.events as events_mod

    for mod in (adapter_mod, cli_mod, events_mod):
        src = Path(mod.__file__).read_text()
        assert "anthropic" not in src, f"anthropic import found in {mod.__file__}"
        assert "claude-agent-sdk" not in src, f"agent-sdk import found in {mod.__file__}"

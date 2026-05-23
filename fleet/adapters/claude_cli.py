import json
import os
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from fleet.adapter import CoderAdapter
from fleet.events import Event
from fleet.models import Task


class ClaudeCLIAdapter(CoderAdapter):
    name = "claude"
    supports_hooks = True

    def build_argv(self, task: Task, artifact_dir: Path) -> list[str]:
        prompt = dedent(f"""\
            You have been assigned Beads task {task.id}: {task.title}

            {task.description or ""}

            Artifact directory (pre-created): {artifact_dir}

            Follow the Loop Task Protocol in CLAUDE.md. Read any existing PLAN.md, STATE.md, \
Q&A.md before doing anything else.
        """).strip()
        return [
            "claude",
            "-p",
            "--output-format", "stream-json",
            "--input-format", "stream-json",
            prompt,
        ]

    def env(self, task: Task, artifact_dir: Path, attempt: int) -> dict[str, str]:
        return {
            "FLEET_TASK_ID": task.id,
            "FLEET_ARTIFACT_DIR": str(artifact_dir),
            "FLEET_ATTEMPT": str(attempt),
        }

    def normalize_event(self, raw_line: str) -> Event | None:  # noqa: PLR0911
        try:
            data = json.loads(raw_line)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        ts = datetime.now(tz=timezone.utc)
        t = data.get("type", "")

        # Soft rate-limit warning (periodic usage envelope)
        if t == "rate_limit_event":
            info = data.get("rate_limit_info", {})
            return Event(
                kind="rate_limit_info",
                raw=data,
                ts=ts,
                rate_info={
                    "usage_pct": info.get("usage_pct") if info.get("usage_pct") is not None
                                 else info.get("usagePct"),
                    "resets_at": info.get("resetsAt"),
                    "status": info.get("status"),
                },
            )

        # Hard rate-limit rejection (HTTP 429 or explicit reject envelope)
        if data.get("api_error_status") == 429 or data.get("error") == "rate_limit":
            return Event(
                kind="rate_limit",
                raw=data,
                ts=ts,
                rate_info={
                    "usage_pct": None,
                    "resets_at": data.get("resetsAt"),
                    "status": "rejected",
                },
            )

        # Session start (system init)
        if t == "system" and data.get("subtype") == "init":
            return Event(
                kind="session_started",
                raw=data,
                ts=ts,
                session_id=data.get("session_id"),
            )

        # System error
        if t == "system" and data.get("subtype") == "error":
            return Event(kind="error", raw=data, ts=ts)

        # Assistant message — may be text or thinking
        if t == "assistant":
            msg = data.get("message", {})
            content = msg.get("content", [])
            usage = msg.get("usage")
            session_id = data.get("session_id")
            # Thinking blocks come first in extended-thinking responses
            for block in content:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    return Event(
                        kind="thinking",
                        raw=data,
                        ts=ts,
                        session_id=session_id,
                        usage=usage,
                    )
            return Event(
                kind="assistant_text",
                raw=data,
                ts=ts,
                session_id=session_id,
                usage=usage,
            )

        # Tool invocation
        if t == "tool_use":
            return Event(
                kind="tool_use",
                raw=data,
                ts=ts,
                tool_name=data.get("name"),
            )

        # Tool result
        if t == "tool_result":
            return Event(
                kind="tool_result",
                raw=data,
                ts=ts,
                tool_name=data.get("name"),
            )

        # Terminal result envelope — session ended
        if t == "result":
            return Event(
                kind="session_ended",
                raw=data,
                ts=ts,
                session_id=data.get("session_id"),
                usage=data.get("usage"),
            )

        return None

    def write_runtime_config(self, project_root: Path, config: object) -> None:
        """Write hook scripts to .fleet/hooks/ and merge fleet entries into .claude/settings.json."""
        project_root = Path(project_root)
        self._install_hooks(project_root)
        self._merge_settings(project_root)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    _FLEET_HOOK_ENTRIES: dict[str, list[dict]] = {
        "PreCompact": [
            {
                "_fleet_managed": True,
                "matcher": "",
                "hooks": [{"type": "command", "command": ".fleet/hooks/precompact.sh"}],
            }
        ],
        "PreToolUse": [
            {
                "_fleet_managed": True,
                "matcher": "AskUserQuestion",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".fleet/hooks/pretool_askuserquestion.sh",
                    }
                ],
            }
        ],
    }

    @classmethod
    def _shipped_hooks_dir(cls) -> Path:
        """Return the hooks/ directory shipped inside the fleet package."""
        return Path(__file__).parent.parent / "hooks"

    @classmethod
    def _install_hooks(cls, project_root: Path) -> None:
        """Copy hook scripts into <project_root>/.fleet/hooks/ with mode 0755."""
        dest_dir = project_root / ".fleet" / "hooks"
        dest_dir.mkdir(parents=True, exist_ok=True)
        src_dir = cls._shipped_hooks_dir()
        for script_name in ("precompact.sh", "pretool_askuserquestion.sh"):
            src = src_dir / script_name
            dst = dest_dir / script_name
            shutil.copy2(src, dst)
            dst.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    @classmethod
    def _merge_settings(cls, project_root: Path) -> None:
        """Merge fleet hook entries into .claude/settings.json atomically."""
        settings_path = project_root / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict = {}
        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = {}

        hooks: dict[str, list] = existing.get("hooks") or {}

        for event_type, fleet_entries in cls._FLEET_HOOK_ENTRIES.items():
            event_hooks = [e for e in hooks.get(event_type, []) if not e.get("_fleet_managed")]
            event_hooks.extend(fleet_entries)
            hooks[event_type] = event_hooks

        merged = dict(existing)
        merged["hooks"] = hooks

        json_text = json.dumps(merged, indent=2) + "\n"
        fd, tmp_path = tempfile.mkstemp(dir=settings_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json_text)
            os.replace(tmp_path, settings_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

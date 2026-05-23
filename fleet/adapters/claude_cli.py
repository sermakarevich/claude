import json
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
        raise NotImplementedError("write_runtime_config is implemented in Task 4")

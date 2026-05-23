from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from typing import Protocol

import structlog

from fleet.adapter import CoderAdapter
from fleet.attempts import count_attempts
from fleet.config import RuntimeConfig
from fleet.events import Event
from fleet.logging_setup import append_event, open_attempt_log
from fleet.models import Task
from fleet.outcomes import TaskOutcome, TaskOutcomeRecord
from fleet.queue import Queue

_STDERR_TAIL_BYTES = 2048


class RateGauge(Protocol):
    def update(self, evt: Event) -> None: ...


class TaskRunner:
    def __init__(
        self,
        task: Task,
        adapter: CoderAdapter,
        queue: Queue,
        config: RuntimeConfig,
        rate_gauge: RateGauge,
        project_root: Path,
        log_root: Path,
        log: structlog.BoundLogger,
    ) -> None:
        self._task = task
        self._adapter = adapter
        self._queue = queue
        self._config = config
        self._rate_gauge = rate_gauge
        self._project_root = project_root
        self._log_root = log_root
        self._log = log
        self._proc: asyncio.subprocess.Process | None = None
        self._cancelled = False

    async def run(self) -> TaskOutcomeRecord:
        task = self._task
        config = self._config

        artifact_root = Path(config.artifact_root)
        if not artifact_root.is_absolute():
            artifact_root = self._project_root / artifact_root
        artifact_dir = artifact_root / task.id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        attempt = count_attempts(self._log_root, task.id) + 1

        with open_attempt_log(self._log_root, task.id, attempt) as attempt_log:
            stderr_path = Path(attempt_log.stderr_file.name)

            argv = self._adapter.build_argv(task, artifact_dir)
            extra_env = self._adapter.env(task, artifact_dir, attempt)
            proc_env = {**os.environ, **extra_env}

            attempt_log.log.info(
                "subprocess_started",
                task_id=task.id,
                attempt=attempt,
                argv=argv,
            )

            proc = await asyncio.create_subprocess_exec(
                *argv,
                env=proc_env,
                cwd=self._project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=attempt_log.stderr_file,
                stdin=asyncio.subprocess.DEVNULL,
            )
            self._proc = proc

            outcome: TaskOutcomeRecord | None = None

            assert proc.stdout is not None
            async for raw_bytes in proc.stdout:
                raw_line = raw_bytes.decode("utf-8", errors="replace").rstrip("\n")
                evt = self._adapter.normalize_event(raw_line)
                if evt is None:
                    continue

                append_event(artifact_dir, evt, attempt)

                if evt.kind == "rate_limit_info":
                    self._rate_gauge.update(evt)
                elif (
                    evt.kind == "rate_limit"
                    and evt.rate_info is not None
                    and evt.rate_info.get("status") == "rejected"
                ):
                    resets_at = evt.rate_info.get("resets_at")
                    reason = (
                        f"rate_limit, sleep until {resets_at}"
                        if resets_at is not None
                        else "rate_limit"
                    )
                    attempt_log.log.warning(
                        "rate_limit_rejected",
                        task_id=task.id,
                        resets_at=resets_at,
                    )
                    self._queue.release(task.id, reason=reason)
                    try:
                        proc.send_signal(signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        try:
                            proc.send_signal(signal.SIGKILL)
                        except (ProcessLookupError, OSError):
                            pass
                        await proc.wait()
                    outcome = TaskOutcomeRecord(
                        outcome=TaskOutcome.RATE_LIMIT,
                        exit_code=proc.returncode,
                        reason=reason,
                        resets_at=resets_at,
                    )
                    break

            exit_code = await proc.wait()

            if outcome is None:
                cp_flag = artifact_dir / ".context_pressure"
                if cp_flag.exists():
                    cp_flag.unlink()
                    outcome = TaskOutcomeRecord(
                        outcome=TaskOutcome.CONTEXT_PRESSURE,
                        exit_code=exit_code,
                        reason="context_pressure hook fired",
                    )
                elif self._cancelled:
                    outcome = TaskOutcomeRecord(
                        outcome=TaskOutcome.FAILURE,
                        exit_code=exit_code,
                        reason="supervisor_shutdown",
                    )
                elif exit_code == 0:
                    blocked = False
                    try:
                        current = self._queue.get(task.id)
                        blocked = current.status == "blocked"
                    except Exception:
                        pass
                    if blocked:
                        outcome = TaskOutcomeRecord(
                            outcome=TaskOutcome.BLOCKED_BY_AGENT,
                            exit_code=exit_code,
                            reason="agent set task to blocked",
                        )
                    else:
                        outcome = TaskOutcomeRecord(
                            outcome=TaskOutcome.SUCCESS,
                            exit_code=exit_code,
                            reason="",
                        )
                else:
                    stderr_tail = _read_file_tail(stderr_path)
                    outcome = TaskOutcomeRecord(
                        outcome=TaskOutcome.FAILURE,
                        exit_code=exit_code,
                        reason=f"subprocess exited with rc={exit_code}",
                        stderr_tail=stderr_tail,
                    )

            attempt_log.log.info(
                "subprocess_exited",
                task_id=task.id,
                attempt=attempt,
                exit_code=exit_code,
                outcome=outcome.outcome.value,
            )
            return outcome

    async def cancel(self) -> None:
        """Send SIGTERM to the child; escalate to SIGKILL after grace period."""
        self._cancelled = True
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        try:
            proc.send_signal(signal.SIGTERM)
        except (ProcessLookupError, OSError):
            return
        try:
            await asyncio.wait_for(
                proc.wait(),
                timeout=float(self._config.shutdown_grace_sec),
            )
        except asyncio.TimeoutError:
            try:
                proc.send_signal(signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            await proc.wait()


def _read_file_tail(path: Path, max_bytes: int = _STDERR_TAIL_BYTES) -> str | None:
    if not path.exists():
        return None
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        return f.read().decode("utf-8", errors="replace")

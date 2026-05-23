import json
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from fleet.models import Task


class BeadsError(RuntimeError):
    pass


class Queue(ABC):
    @abstractmethod
    def claim_next(self, claimer_id: str) -> Task | None: ...

    @abstractmethod
    def release(self, task_id: str, reason: str = "") -> None: ...

    @abstractmethod
    def set_blocked(self, task_id: str, reason: str) -> None: ...

    @abstractmethod
    def close(self, task_id: str, reason: str = "completed") -> None: ...

    @abstractmethod
    def comment(self, task_id: str, body: str) -> None: ...

    @abstractmethod
    def get(self, task_id: str) -> Task: ...

    @abstractmethod
    def list_ready(self, limit: int = 50) -> list[Task]: ...

    @abstractmethod
    def create_task(
        self,
        title: str,
        description: str | None = None,
        depends_on: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> Task: ...


class BeadsQueue(Queue):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def _bd(self, *args: str, json_envelope: bool = True, actor: str | None = None) -> dict | None:
        env = {**os.environ}
        if json_envelope:
            env["BD_JSON_ENVELOPE"] = "1"
        if actor is not None:
            env["BEADS_ACTOR"] = actor
        result = subprocess.run(
            ["bd", *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=self.repo_root,
        )
        if result.returncode != 0:
            raise BeadsError(result.stderr.strip())
        if json_envelope and result.stdout.strip():
            return json.loads(result.stdout)
        return None

    def claim_next(self, claimer_id: str) -> Task | None:
        ready = self._bd("ready", "--json", "--limit", "10")
        items: list = ready.get("data", ready) if isinstance(ready, dict) else (ready or [])
        if not isinstance(items, list):
            items = []
        for cand in items:
            try:
                self._bd("update", cand["id"], "--claim", json_envelope=False, actor=claimer_id)
            except BeadsError:
                continue
            return Task(
                id=cand["id"],
                title=cand["title"],
                description=cand.get("description"),
                status="in_progress",
            )
        return None

    def release(self, task_id: str, reason: str = "") -> None:
        self._bd("update", task_id, "--status", "open", "--assignee", "", json_envelope=False)
        if reason:
            self._bd("comment", task_id, reason, json_envelope=False)

    def set_blocked(self, task_id: str, reason: str) -> None:
        self._bd("update", task_id, "--status", "blocked", "--notes", reason, json_envelope=False)

    def close(self, task_id: str, reason: str = "completed") -> None:
        self._bd("close", task_id, "--reason", reason, json_envelope=False)

    def comment(self, task_id: str, body: str) -> None:
        self._bd("comment", task_id, body, json_envelope=False)

    def get(self, task_id: str) -> Task:
        data = self._bd("show", task_id, "--json")
        if data is None:
            raise BeadsError(f"bd show {task_id}: empty response")
        body = data.get("data", data) if isinstance(data, dict) else data
        return Task(
            id=body["id"],
            title=body["title"],
            description=body.get("description"),
            status=body.get("status", "open"),
        )

    def list_ready(self, limit: int = 50) -> list[Task]:
        data = self._bd("ready", "--json", "--limit", str(limit))
        items: list = data.get("data", data) if isinstance(data, dict) else (data or [])
        if not isinstance(items, list):
            items = []
        return [
            Task(
                id=item["id"],
                title=item["title"],
                description=item.get("description"),
                status=item.get("status", "open"),
            )
            for item in items
        ]

    def create_task(
        self,
        title: str,
        description: str | None = None,
        depends_on: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> Task:
        args = ["create", "--title", title]
        if description:
            args += ["--description", description]
        result = subprocess.run(
            ["bd", *args],
            capture_output=True,
            text=True,
            env={**os.environ},
            cwd=self.repo_root,
        )
        if result.returncode != 0:
            raise BeadsError(result.stderr.strip() or "bd create failed")
        # bd create prints the new task id as the last token on stdout
        tokens = result.stdout.strip().split()
        task_id = tokens[-1] if tokens else ""
        if not task_id:
            raise BeadsError("bd create returned no task id")
        if depends_on:
            for dep_id in depends_on:
                self._bd("dep", "add", task_id, dep_id, json_envelope=False)
        return self.get(task_id)

from abc import ABC, abstractmethod
from pathlib import Path

from fleet.events import Event
from fleet.models import Task


class CoderAdapter(ABC):
    name: str
    supports_hooks: bool

    @abstractmethod
    def build_argv(self, task: Task, artifact_dir: Path) -> list[str]:
        """Return the argv list to spawn the coder CLI subprocess."""

    @abstractmethod
    def env(self, task: Task, artifact_dir: Path, attempt: int) -> dict[str, str]:
        """Return env-var overlay merged over os.environ when spawning.

        MUST include FLEET_TASK_ID, FLEET_ARTIFACT_DIR, FLEET_ATTEMPT.
        MUST NOT include ANTHROPIC_API_KEY (owned by the CLI).
        """

    @abstractmethod
    def normalize_event(self, raw_line: str) -> Event | None:
        """Parse one line of subprocess stdout into a normalized Event.

        Returns None for malformed JSON or lines the adapter wants to drop.
        SHALL be pure: no I/O, no logging, no side effects.
        """

    @abstractmethod
    def write_runtime_config(self, project_root: Path, config: object) -> None:
        """Write .claude/settings.json or equivalent before the subprocess.

        Implemented in Task 4. Raise NotImplementedError until then.
        """

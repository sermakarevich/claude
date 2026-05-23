from dataclasses import dataclass
from enum import Enum


class TaskOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RATE_LIMIT = "rate_limit"
    CONTEXT_PRESSURE = "context_pressure"
    BLOCKED_BY_AGENT = "blocked_by_agent"


@dataclass
class TaskOutcomeRecord:
    outcome: TaskOutcome
    exit_code: int | None = None
    reason: str = ""
    resets_at: int | None = None
    stderr_tail: str | None = None

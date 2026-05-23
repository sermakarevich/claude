from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

EventKind = Literal[
    "assistant_text",
    "tool_use",
    "tool_result",
    "thinking",
    "rate_limit",
    "rate_limit_info",
    "context_pressure",
    "session_started",
    "session_ended",
    "error",
    "result",
]


@dataclass
class Event:
    kind: EventKind
    raw: dict
    ts: datetime
    session_id: str | None = None
    tool_name: str | None = None
    # {input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}
    usage: dict | None = None
    # {usage_pct: float|None, resets_at: int|None, status: str|None}
    rate_info: dict | None = None
    extra: dict = field(default_factory=dict)

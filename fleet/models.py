from dataclasses import dataclass


@dataclass
class Task:
    id: str
    title: str
    description: str | None
    status: str

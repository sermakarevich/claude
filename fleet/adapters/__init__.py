from fleet.adapter import CoderAdapter
from fleet.adapters.claude_cli import ClaudeCLIAdapter

_REGISTRY: dict[str, type[CoderAdapter]] = {
    "claude": ClaudeCLIAdapter,
}


def get_adapter(name: str) -> type[CoderAdapter]:
    """Return the adapter class for the given name, or raise ValueError."""
    try:
        return _REGISTRY[name]
    except KeyError:
        available = list(_REGISTRY)
        raise ValueError(f"Unknown adapter {name!r}. Available: {available}") from None

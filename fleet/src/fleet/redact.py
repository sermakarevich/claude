_EXACT_KEYS = frozenset(
    {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY"}
)
_SUBSTRING_KEYS = ("password", "secret", "token")


def _is_credential_key(key: str) -> bool:
    return key in _EXACT_KEYS or any(s in key.lower() for s in _SUBSTRING_KEYS)


def redact(payload: dict) -> dict:
    """Return a new dict with credential keys replaced by '<redacted>'."""
    result = {}
    for k, v in payload.items():
        if _is_credential_key(k):
            result[k] = "<redacted>"
        elif isinstance(v, dict):
            result[k] = redact(v)
        else:
            result[k] = v
    return result

from fleet.redact import redact


def test_exact_credential_keys_redacted():
    payload = {
        "ANTHROPIC_API_KEY": "sk-ant-123",
        "ANTHROPIC_AUTH_TOKEN": "tok-456",
        "OPENAI_API_KEY": "sk-openai-789",
        "GEMINI_API_KEY": "gm-abc",
    }
    result = redact(payload)
    assert all(v == "<redacted>" for v in result.values())


def test_substring_keys_redacted():
    result = redact({"db_password": "secret!", "my_secret": "xyz", "access_token": "tok"})
    assert result["db_password"] == "<redacted>"
    assert result["my_secret"] == "<redacted>"
    assert result["access_token"] == "<redacted>"


def test_non_credential_keys_unchanged():
    payload = {"name": "test", "count": 42, "enabled": True}
    assert redact(payload) == payload


def test_nested_dicts_redacted_recursively():
    payload = {
        "outer": {"ANTHROPIC_API_KEY": "sk-key", "safe": "value"},
        "top_level": "ok",
    }
    result = redact(payload)
    assert result["outer"]["ANTHROPIC_API_KEY"] == "<redacted>"
    assert result["outer"]["safe"] == "value"
    assert result["top_level"] == "ok"


def test_input_dict_not_mutated():
    original = {"ANTHROPIC_API_KEY": "sk-key", "name": "test"}
    snapshot = dict(original)
    redact(original)
    assert original == snapshot


def test_empty_dict():
    assert redact({}) == {}

import pytest

from gopilot.config import _load_llm_config


def test_load_llm_config_defaults_to_gemini(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    cfg = _load_llm_config()

    assert cfg.provider == "gemini"
    assert cfg.model_name == "gemini-1.5-flash"


def test_load_llm_config_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "gpt-4.1-mini")

    cfg = _load_llm_config()

    assert cfg.provider == "openai"
    assert cfg.model_name == "gpt-4.1-mini"


def test_load_llm_config_claude_missing_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        _load_llm_config()

"""The LLM call skips a rate-limited model for the next one instead of keeping the person waiting."""

from __future__ import annotations

import types

import groq
import pytest

from app.analysis.instagram import llm


class _Limited(groq.RateLimitError):
    def __init__(self, wait: str):
        Exception.__init__(self, f"Rate limit reached. Please try again in {wait}.")


def _client(behaviour: dict[str, object], calls: list[str]):
    def create(model, messages):
        calls.append(model)
        out = behaviour[model]
        if isinstance(out, Exception):
            raise out
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=out))])

    return lambda api_key: types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(llm.settings, "groq_api_key", "test")
    monkeypatch.setattr(llm.settings, "groq_model", "big")
    monkeypatch.setattr(llm.settings, "groq_fallback_models", "small,other")
    slept: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    return slept


def test_rate_limited_model_falls_back_at_once(monkeypatch, settings):
    calls: list[str] = []
    monkeypatch.setattr(groq, "Groq", _client({"big": _Limited("12m30s"), "small": "answer", "other": "x"}, calls))
    assert llm.get_llm()("hi") == "answer"
    assert calls == ["big", "small"] and settings == []          # no waiting at all


def test_long_limits_everywhere_fail_fast_with_a_clear_message(monkeypatch, settings):
    calls: list[str] = []
    limited = {m: _Limited("9m10s") for m in ("big", "small", "other")}
    monkeypatch.setattr(groq, "Groq", _client(limited, calls))
    with pytest.raises(RuntimeError, match="busy"):
        llm.get_llm()("hi")
    assert settings == []                                         # never sleeps for minutes


def test_short_limit_everywhere_waits_once_then_retries(monkeypatch, settings):
    calls: list[str] = []
    state = {"n": 0}
    behaviour = {"big": _Limited("3.5s"), "small": _Limited("2s"), "other": _Limited("4s")}

    def flip(api_key):
        client = _client(behaviour, calls)(api_key)
        original = client.chat.completions.create

        def create(model, messages):
            state["n"] += 1
            if state["n"] > 3:
                behaviour["big"] = "late answer"
            return original(model, messages)

        client.chat.completions.create = create
        return client

    monkeypatch.setattr(groq, "Groq", flip)
    assert llm.get_llm()("hi") == "late answer"
    assert settings == [3.0]                                      # one short wait (2 s + 1 s margin)

"""Tests for runner adapters (PythonRunner, HttpRunner)."""

from __future__ import annotations

import pytest

from auxilab_eval.runners import HttpRunner, PythonRunner


def test_python_runner_returns_value_with_timing():
    def agent(payload: dict) -> dict:
        return {"echo": payload.get("x")}

    runner = PythonRunner(agent)
    result = runner.run({"x": 42})

    assert result.ok is True
    assert result.error is None
    assert result.output == {"echo": 42}
    assert result.duration_ms >= 0


def test_python_runner_captures_exception_as_structured_error():
    def boom(payload: dict) -> dict:
        raise ValueError("kaboom")

    runner = PythonRunner(boom)
    result = runner.run({})

    assert result.ok is False
    assert "ValueError" in result.error
    assert "kaboom" in result.error
    assert result.traceback is not None
    assert result.output is None


def test_python_runner_supports_async_callable():
    async def agent(payload):
        return {"async": True, "n": payload["n"]}

    runner = PythonRunner(agent)
    result = runner.run({"n": 7})

    assert result.ok is True
    assert result.output == {"async": True, "n": 7}


def test_http_runner_rejects_object_without_invoke_for_langgraph():
    # HttpRunner has its own validation: empty url should raise.
    with pytest.raises(ValueError):
        HttpRunner("")


def test_python_runner_rejects_non_callable():
    with pytest.raises(TypeError):
        PythonRunner("not a callable")  # type: ignore[arg-type]

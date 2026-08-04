"""Tests for the built-in evaluators (excluding network-bound LLM judge)."""

from __future__ import annotations

import pytest

from auxilab_eval.evaluators import (
    ExactMatchEvaluator,
    JsonSchemaEvaluator,
    RegexEvaluator,
)
from auxilab_eval.schema import EvaluatorSpec, TestCase


def _tc(expected: dict, evaluator: EvaluatorSpec) -> TestCase:
    return TestCase(
        id="t1",
        input={},
        expected=expected,
        evaluators=[evaluator],
    )


# ---------------------------------------------------------------------------
# exact
# ---------------------------------------------------------------------------


def test_exact_match_passes_for_equal_field():
    spec = EvaluatorSpec(type="exact", field="decision")
    tc = _tc({"decision": "approve"}, spec)
    result = ExactMatchEvaluator(spec).evaluate(tc, {"decision": "approve"})
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_fails_for_mismatch():
    spec = EvaluatorSpec(type="exact", field="decision")
    tc = _tc({"decision": "approve"}, spec)
    result = ExactMatchEvaluator(spec).evaluate(tc, {"decision": "reject"})
    assert result.passed is False
    assert result.score == 0.0
    assert "approve" in result.detail
    assert "reject" in result.detail


def test_exact_match_with_inline_expected_overrides_test_case():
    spec = EvaluatorSpec(type="exact", field="decision", expected="reject")
    tc = _tc({"decision": "approve"}, spec)  # ignored because spec.expected is set
    result = ExactMatchEvaluator(spec).evaluate(tc, {"decision": "reject"})
    assert result.passed is True


# ---------------------------------------------------------------------------
# regex
# ---------------------------------------------------------------------------


def test_regex_matches_pattern_in_field():
    spec = EvaluatorSpec(type="regex", field="reason", pattern=r"(?i)duplicate")
    tc = _tc({}, spec)
    result = RegexEvaluator(spec).evaluate(tc, {"reason": "Looks like a Duplicate."})
    assert result.passed is True


def test_regex_fails_when_pattern_missing():
    spec = EvaluatorSpec(type="regex", field="reason")
    tc = _tc({}, spec)
    result = RegexEvaluator(spec).evaluate(tc, {"reason": "anything"})
    assert result.passed is False
    assert "regex" in result.detail.lower()


def test_regex_handles_invalid_pattern_gracefully():
    spec = EvaluatorSpec(type="regex", field="reason", pattern="[unclosed")
    tc = _tc({}, spec)
    result = RegexEvaluator(spec).evaluate(tc, {"reason": "anything"})
    assert result.passed is False
    assert "Invalid regex" in result.detail


# ---------------------------------------------------------------------------
# json schema
# ---------------------------------------------------------------------------


def test_json_schema_passes_for_valid_output():
    schema = {
        "type": "object",
        "required": ["decision", "confidence"],
        "properties": {
            "decision": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }
    spec = EvaluatorSpec(type="json_schema", schema=schema)
    tc = _tc({}, spec)
    result = JsonSchemaEvaluator(spec).evaluate(
        tc, {"decision": "approve", "confidence": 0.9}
    )
    assert result.passed is True


def test_json_schema_fails_for_missing_field():
    schema = {
        "type": "object",
        "required": ["decision", "confidence"],
        "properties": {
            "decision": {"type": "string"},
            "confidence": {"type": "number"},
        },
    }
    spec = EvaluatorSpec(type="json_schema", schema=schema)
    tc = _tc({}, spec)
    result = JsonSchemaEvaluator(spec).evaluate(tc, {"decision": "approve"})
    assert result.passed is False
    # Errors should reference the missing 'confidence' field.
    paths = [list(e.get("path", [])) for e in result.breakdown["errors"]]
    assert any("confidence" in str(p) or "required" in str(e).lower()
               for p, e in zip(paths, result.breakdown["errors"])) or \
        "confidence" in result.detail

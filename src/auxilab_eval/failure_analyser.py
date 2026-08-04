"""LLM-powered failure classifier.

When a test case fails, the harness asks Claude to bucket the failure into
one of the canonical types and return a structured report we can use in the
HTML report and trend charts.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from auxilab_eval.schema import TestCase


FAILURE_TYPES: tuple[str, ...] = (
    "Hallucination",
    "Tool Call Error",
    "Reasoning Error",
    "Output Format Error",
    "Incomplete Task",
    "Unexpected Behaviour",
)


@dataclass
class FailureReport:
    """Structured failure report attached to a failing test case."""

    failure_type: str
    confidence: float
    summary: str
    evidence: list[str] = field(default_factory=list)
    raw_output: Any = None
    error: Optional[str] = None  # only when the analyser itself failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_type": self.failure_type,
            "confidence": self.confidence,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "raw_output": self.raw_output,
            "error": self.error,
        }


_SYSTEM_PROMPT = f"""You are a senior AI engineer triaging failures in an
agentic AI system. You will classify each failure into exactly one of the
following canonical types:

{", ".join(FAILURE_TYPES)}

Definitions:
- Hallucination: the agent fabricated facts, identifiers, or values not
  present in the input or grounded data.
- Tool Call Error: the agent called the wrong tool, passed invalid
  arguments, or ignored required tool calls.
- Reasoning Error: the agent's logic, math, or inference is wrong even though
  the inputs and tools were correct.
- Output Format Error: content is correct but the structure/schema is wrong
  (missing fields, wrong types, malformed JSON, etc.).
- Incomplete Task: the agent stopped early or produced a partial answer.
- Unexpected Behaviour: catch-all for anything that doesn't fit above.

You MUST respond with ONLY a JSON object — no markdown, no prose — with this
exact shape:

{{
  "failure_type": "<one of the canonical types verbatim>",
  "confidence": <float between 0 and 1>,
  "summary": "<one sentence explaining the failure>",
  "evidence": ["<short bullet>", "<short bullet>", ...]
}}
"""


class FailureAnalyser:
    """Calls Claude to classify a failed test case."""

    def __init__(self, *, model: Optional[str] = None) -> None:
        self.model = model or os.getenv(
            "AUXILAB_EVAL_MODEL", "claude-haiku-4-5-20251001"
        )
        self._client = None

    def analyse(
        self,
        test_case: TestCase,
        actual_output: Any,
        evaluator_results: list[dict[str, Any]],
        runner_error: Optional[str] = None,
    ) -> FailureReport:
        """Produce a `FailureReport` for a failed test case.

        Falls back to a heuristic classification when no API key is available
        or the API call itself fails — we never want a missing key to crash
        a test run.
        """
        try:
            return self._call(test_case, actual_output, evaluator_results, runner_error)
        except Exception as exc:  # noqa: BLE001
            return self._heuristic_fallback(
                test_case, actual_output, evaluator_results, runner_error,
                error=str(exc),
            )

    # -- internals ----------------------------------------------------------

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; using heuristic fallback.")
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Install `anthropic` to enable failure analysis.") from exc
        self._client = Anthropic(api_key=api_key)
        return self._client

    def _call(
        self,
        test_case: TestCase,
        actual_output: Any,
        evaluator_results: list[dict[str, Any]],
        runner_error: Optional[str],
    ) -> FailureReport:
        client = self._client_or_raise()
        payload = {
            "test_case": {
                "id": test_case.id,
                "description": test_case.description or "",
                "input": test_case.input,
                "expected": test_case.expected,
            },
            "actual_output": actual_output,
            "evaluator_results": evaluator_results,
            "runner_error": runner_error,
        }
        response = client.messages.create(
            model=self.model,
            max_tokens=600,
            system=_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    "Classify the following failure. Reply with the JSON object only.\n\n"
                    + json.dumps(payload, indent=2, default=str)
                ),
            }],
        )
        text = _extract_text(response)
        data = _parse_json_object(text)
        return _coerce_report(data, raw_output=actual_output)

    def _heuristic_fallback(
        self,
        test_case: TestCase,
        actual_output: Any,
        evaluator_results: list[dict[str, Any]],
        runner_error: Optional[str],
        *,
        error: str,
    ) -> FailureReport:
        if runner_error:
            failure_type = "Tool Call Error"
            summary = f"Runner raised an exception: {runner_error}"
        elif actual_output is None:
            failure_type = "Incomplete Task"
            summary = "Agent returned no output."
        elif not isinstance(actual_output, (dict, list, str, int, float, bool)):
            failure_type = "Output Format Error"
            summary = f"Output is of unexpected type: {type(actual_output).__name__}."
        else:
            failure_type = "Unexpected Behaviour"
            summary = "One or more evaluators failed; see breakdown."

        evidence = [
            f"{r.get('evaluator')}: {r.get('detail')}"
            for r in evaluator_results
            if not r.get("passed")
        ][:5]

        return FailureReport(
            failure_type=failure_type,
            confidence=0.4,
            summary=summary,
            evidence=evidence,
            raw_output=actual_output,
            error=f"heuristic fallback ({error})",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_text(response) -> str:
    blocks = getattr(response, "content", None) or []
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
        elif isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
    return "\n".join(parts).strip()


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_object(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("Empty analyser response.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(text)
        if not match:
            raise ValueError(f"No JSON object found: {text[:200]}")
        return json.loads(match.group(0))


def _coerce_report(data: dict[str, Any], *, raw_output: Any) -> FailureReport:
    failure_type = str(data.get("failure_type") or "Unexpected Behaviour")
    if failure_type not in FAILURE_TYPES:
        # Map free-form responses to the closest canonical bucket.
        lower = failure_type.lower()
        match = next(
            (t for t in FAILURE_TYPES if t.lower() in lower or lower in t.lower()),
            "Unexpected Behaviour",
        )
        failure_type = match
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    evidence = data.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    return FailureReport(
        failure_type=failure_type,
        confidence=confidence,
        summary=str(data.get("summary") or ""),
        evidence=[str(e) for e in evidence][:8],
        raw_output=raw_output,
    )

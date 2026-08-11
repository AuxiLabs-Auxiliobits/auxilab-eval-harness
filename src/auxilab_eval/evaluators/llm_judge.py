"""LLM-as-judge evaluator (Claude).

Asks Claude to score the agent output against a per-criterion rubric and
returns a structured JSON score with a brief rationale per criterion.

This is the most distinctive evaluator in the harness — see the prompt in
`_JUDGE_SYSTEM_PROMPT` for the full scoring contract.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from auxilab_eval._utils import get_field, stringify
from auxilab_eval.evaluators.base import EvaluationResult, Evaluator
from auxilab_eval.schema import TestCase


_JUDGE_SYSTEM_PROMPT = """You are a strict but fair evaluator of agentic AI outputs.

You will receive:
  1. A test case description and the original input payload
  2. The expected output (may be partial)
  3. The actual output produced by the agent
  4. A scoring rubric: a JSON object mapping criterion name -> description

You MUST score every criterion on a continuous scale from 0.0 to 1.0, where
  1.0 = fully meets the criterion
  0.5 = partially meets the criterion
  0.0 = fails the criterion entirely

You MUST respond with ONLY a JSON object — no markdown, no prose before or
after — with the following exact shape:

{
  "scores": {
    "<criterion_name>": {
      "score": <float between 0 and 1>,
      "rationale": "<one or two sentence justification>"
    },
    ...
  },
  "overall_comment": "<one sentence, plain English, summarising the verdict>"
}

Be evidence-based: cite specific elements of the actual output. Penalise
hallucinated facts, missing required fields, and unprofessional or unsafe
language."""


class LLMJudgeEvaluator(Evaluator):
    """Score the agent output against a rubric using Claude."""

    name = "llm_judge"

    def __init__(self, spec) -> None:
        super().__init__(spec)
        self._client = None  # lazy

    # -- public API ---------------------------------------------------------

    def evaluate(self, test_case: TestCase, output: Any) -> EvaluationResult:
        rubric = self.spec.rubric
        if rubric is None:
            return EvaluationResult(
                evaluator="llm_judge",
                passed=False,
                score=0.0,
                detail="No rubric provided for the LLM judge.",
                weight=self.spec.weight,
            )

        actual = get_field(output, self.spec.field)
        expected = (
            self.spec.expected
            if self.spec.expected is not None
            else (
                test_case.expected.get(self.spec.field)
                if self.spec.field else test_case.expected
            )
        )

        try:
            verdict = self._call_judge(test_case, expected, actual, rubric)
        except Exception as exc:  # noqa: BLE001
            return EvaluationResult(
                evaluator="llm_judge",
                passed=False,
                score=0.0,
                detail=f"Judge call failed: {exc}",
                weight=self.spec.weight,
            )

        weights = rubric.normalised_weights()
        scores = verdict.get("scores", {})
        weighted = 0.0
        per_criterion: dict[str, Any] = {}
        for name in rubric.criteria:
            entry = scores.get(name) or {}
            try:
                s = float(entry.get("score", 0.0))
            except (TypeError, ValueError):
                s = 0.0
            s = max(0.0, min(1.0, s))
            weighted += s * weights[name]
            per_criterion[name] = {
                "score": s,
                "rationale": entry.get("rationale", ""),
                "weight": weights[name],
            }

        passed = weighted >= float(self.spec.threshold)
        return EvaluationResult(
            evaluator="llm_judge",
            passed=passed,
            score=weighted,
            detail=verdict.get("overall_comment") or (
                f"Weighted judge score: {weighted:.2f}"
            ),
            breakdown={
                "criteria": per_criterion,
                "raw": verdict,
                "threshold": self.spec.threshold,
            },
            weight=self.spec.weight,
        )

    # -- internals ----------------------------------------------------------

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; the LLM judge needs it to call Claude."
            )
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Install `anthropic` to use the LLM judge: pip install anthropic"
            ) from exc
        self._client = Anthropic(api_key=api_key)
        return self._client

    def _call_judge(
        self,
        test_case: TestCase,
        expected: Any,
        actual: Any,
        rubric,
    ) -> dict[str, Any]:
        client = self._client_or_raise()
        model = os.getenv("AUXILAB_EVAL_MODEL", "claude-haiku-4-5-20251001")

        user_payload = {
            "test_case": {
                "id": test_case.id,
                "description": test_case.description or "",
                "input": test_case.input,
            },
            "expected_output": expected,
            "actual_output": actual,
            "rubric": rubric.criteria,
        }

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_JUDGE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Evaluate the following agent output. Respond with the "
                        "exact JSON shape described in the system prompt.\n\n"
                        + json.dumps(user_payload, indent=2, default=str)
                    ),
                }
            ],
        )
        text = _extract_text(response)
        return _parse_json_object(text)


def _extract_text(response) -> str:
    """Best-effort extraction of plain text from an Anthropic response."""
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
    """Parse a JSON object from a possibly-noisy LLM response."""
    if not text:
        raise ValueError("Empty judge response.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(text)
        if not match:
            raise ValueError(f"No JSON object found in judge response: {text[:200]}")
        return json.loads(match.group(0))

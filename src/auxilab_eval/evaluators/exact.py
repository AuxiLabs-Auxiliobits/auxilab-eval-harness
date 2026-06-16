"""Strict equality evaluator."""

from __future__ import annotations

from typing import Any

from auxilab_eval._utils import get_field
from auxilab_eval.evaluators.base import EvaluationResult, Evaluator
from auxilab_eval.schema import TestCase


class ExactMatchEvaluator(Evaluator):
    """Pass when `output[field]` exactly equals the expected value."""

    name = "exact"

    def evaluate(self, test_case: TestCase, output: Any) -> EvaluationResult:
        field = self.spec.field
        expected = (
            self.spec.expected
            if self.spec.expected is not None
            else (test_case.expected.get(field) if field else test_case.expected)
        )
        actual = get_field(output, field)
        passed = actual == expected
        return EvaluationResult(
            evaluator=f"exact:{field or '<root>'}",
            passed=passed,
            score=1.0 if passed else 0.0,
            detail=(
                "Match." if passed
                else f"Expected {expected!r}, got {actual!r}."
            ),
            breakdown={"expected": expected, "actual": actual},
            weight=self.spec.weight,
        )

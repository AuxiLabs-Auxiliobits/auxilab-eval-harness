"""Regex match evaluator."""

from __future__ import annotations

import re
from typing import Any

from auxilab_eval._utils import get_field, stringify
from auxilab_eval.evaluators.base import EvaluationResult, Evaluator
from auxilab_eval.schema import TestCase


class RegexEvaluator(Evaluator):
    """Pass when the regex pattern matches the (stringified) field value.

    Pattern is taken from `spec.pattern` (preferred) or the matching key in
    `test_case.expected`.
    """

    name = "regex"

    def evaluate(self, test_case: TestCase, output: Any) -> EvaluationResult:
        field = self.spec.field
        pattern = self.spec.pattern or (
            test_case.expected.get(field) if field else None
        )
        if not pattern:
            return EvaluationResult(
                evaluator=f"regex:{field or '<root>'}",
                passed=False,
                score=0.0,
                detail="No regex pattern provided.",
                weight=self.spec.weight,
            )

        actual = stringify(get_field(output, field))
        try:
            match = re.search(pattern, actual)
        except re.error as exc:
            return EvaluationResult(
                evaluator=f"regex:{field or '<root>'}",
                passed=False,
                score=0.0,
                detail=f"Invalid regex: {exc}",
                breakdown={"pattern": pattern},
                weight=self.spec.weight,
            )

        passed = match is not None
        return EvaluationResult(
            evaluator=f"regex:{field or '<root>'}",
            passed=passed,
            score=1.0 if passed else 0.0,
            detail=(
                f"Matched {match.group(0)!r}." if passed
                else f"Pattern {pattern!r} did not match {actual!r}."
            ),
            breakdown={"pattern": pattern, "actual": actual},
            weight=self.spec.weight,
        )

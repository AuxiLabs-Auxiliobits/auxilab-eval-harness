"""JSON Schema validation evaluator."""

from __future__ import annotations

from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from auxilab_eval._utils import get_field
from auxilab_eval.evaluators.base import EvaluationResult, Evaluator
from auxilab_eval.schema import TestCase


class JsonSchemaEvaluator(Evaluator):
    """Pass when the (sub-)output validates against the configured JSON Schema."""

    name = "json_schema"

    def evaluate(self, test_case: TestCase, output: Any) -> EvaluationResult:
        schema = self.spec.schema
        if not schema:
            return EvaluationResult(
                evaluator=f"json_schema:{self.spec.field or '<root>'}",
                passed=False,
                score=0.0,
                detail="No JSON schema provided.",
                weight=self.spec.weight,
            )
        target = get_field(output, self.spec.field)
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(target), key=lambda e: e.path)
        passed = not errors
        return EvaluationResult(
            evaluator=f"json_schema:{self.spec.field or '<root>'}",
            passed=passed,
            score=1.0 if passed else 0.0,
            detail=(
                "Schema validation passed." if passed
                else "; ".join(e.message for e in errors[:3])
            ),
            breakdown={
                "errors": [
                    {"path": list(e.path), "message": e.message} for e in errors
                ]
            },
            weight=self.spec.weight,
        )

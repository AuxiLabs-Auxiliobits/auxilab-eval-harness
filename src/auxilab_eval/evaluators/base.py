"""Evaluator base class + dispatch."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from auxilab_eval.schema import EvaluatorSpec, TestCase


@dataclass
class EvaluationResult:
    """Outcome of running a single evaluator against an agent output."""

    evaluator: str           # human-readable name (e.g. "exact", "llm_judge:correctness")
    passed: bool
    score: float             # in [0, 1]
    detail: str = ""         # short, user-facing explanation
    breakdown: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


class Evaluator(ABC):
    """Base class for all evaluators."""

    name: str = "evaluator"

    def __init__(self, spec: EvaluatorSpec) -> None:
        self.spec = spec

    @abstractmethod
    def evaluate(self, test_case: TestCase, output: Any) -> EvaluationResult:
        """Score the agent `output` for `test_case`."""


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def get_evaluator(spec: EvaluatorSpec) -> Evaluator:
    """Resolve an `EvaluatorSpec` to a concrete `Evaluator` instance."""
    # Imports are local to avoid a circular import (each evaluator imports
    # this module for the base class).
    from auxilab_eval.evaluators.exact import ExactMatchEvaluator
    from auxilab_eval.evaluators.regex import RegexEvaluator
    from auxilab_eval.evaluators.json_schema import JsonSchemaEvaluator
    from auxilab_eval.evaluators.semantic import SemanticSimilarityEvaluator
    from auxilab_eval.evaluators.llm_judge import LLMJudgeEvaluator

    mapping: dict[str, type[Evaluator]] = {
        "exact": ExactMatchEvaluator,
        "regex": RegexEvaluator,
        "json_schema": JsonSchemaEvaluator,
        "semantic": SemanticSimilarityEvaluator,
        "llm_judge": LLMJudgeEvaluator,
    }
    cls = mapping.get(spec.type)
    if cls is None:
        raise ValueError(f"Unknown evaluator type: {spec.type!r}")
    return cls(spec)

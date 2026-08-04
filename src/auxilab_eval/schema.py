"""Pydantic schema for test cases, evaluator specs, and rubrics.

A test case file is a YAML or JSON document containing a list of `TestCase`
objects. See `demo/test_cases/ap_exception_tests.yaml` for an example.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Rubric & evaluator specs
# ---------------------------------------------------------------------------

EvaluatorType = Literal[
    "exact",
    "regex",
    "json_schema",
    "semantic",
    "llm_judge",
]


class Rubric(BaseModel):
    """A scoring rubric used by the LLM-judge evaluator.

    `criteria` maps a criterion name to a human-readable description that the
    LLM will score 0–1 against. `weights` (optional) gives a relative weight
    per criterion. Missing weights default to equal weighting.
    """

    criteria: dict[str, str] = Field(
        ..., description="Mapping of criterion name -> description for the judge"
    )
    weights: dict[str, float] = Field(default_factory=dict)

    @field_validator("criteria")
    @classmethod
    def _at_least_one_criterion(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("Rubric must have at least one criterion.")
        return v

    def normalised_weights(self) -> dict[str, float]:
        """Return weights that sum to 1.0, falling back to equal weighting."""
        if not self.weights:
            n = len(self.criteria)
            return {k: 1.0 / n for k in self.criteria}
        # Default missing criteria to 0
        raw = {k: float(self.weights.get(k, 0.0)) for k in self.criteria}
        total = sum(raw.values())
        if total <= 0:
            n = len(self.criteria)
            return {k: 1.0 / n for k in self.criteria}
        return {k: v / total for k, v in raw.items()}


class EvaluatorSpec(BaseModel):
    """A single evaluator attached to a test case.

    Examples:
        - {type: exact, field: decision}
        - {type: regex, field: reason, pattern: "(?i)duplicate"}
        - {type: semantic, field: explanation, threshold: 0.75}
        - {type: json_schema, schema: {...}}
        - {type: llm_judge, rubric: {criteria: {...}, weights: {...}}}
    """

    type: EvaluatorType
    # Field path inside the agent output (e.g. "decision" or "result.reason").
    # When omitted, the evaluator operates on the whole output.
    field: Optional[str] = None
    # Common knobs (only the relevant ones are read by each evaluator)
    pattern: Optional[str] = None
    threshold: float = 0.7
    # Stored as `json_schema` to avoid shadowing pydantic's BaseModel.schema().
    # YAML / JSON files may use either `schema` (preferred) or `json_schema`.
    json_schema: Optional[dict[str, Any]] = Field(
        default=None, alias="schema", serialization_alias="schema",
    )
    rubric: Optional[Rubric] = None
    # Weight of this evaluator in the per-test-case aggregate score.
    weight: float = 1.0
    # Optional override for the field's expected value. When None, the
    # corresponding key from `TestCase.expected` is used.
    expected: Optional[Any] = None

    model_config = ConfigDict(populate_by_name=True)

    # Back-compat: many call sites read `spec.schema`.
    @property
    def schema(self) -> Optional[dict[str, Any]]:
        return self.json_schema


# ---------------------------------------------------------------------------
# Test case
# ---------------------------------------------------------------------------


class TestCase(BaseModel):
    """A single agent test case."""

    # Tell pytest not to collect this Pydantic model as a test class.
    __test__ = False

    id: str = Field(..., description="Stable, unique identifier")
    description: Optional[str] = None
    input: dict[str, Any] = Field(
        ..., description="Payload passed to the agent runner"
    )
    expected: dict[str, Any] = Field(
        default_factory=dict,
        description="Expected output fields (keyed by field path)",
    )
    evaluators: list[EvaluatorSpec] = Field(
        default_factory=list,
        description="Evaluators to apply to the agent output",
    )
    tags: list[str] = Field(default_factory=list)
    # Threshold for the per-test-case aggregate score. A test case passes when
    # every evaluator passes AND the weighted score is >= `pass_threshold`.
    pass_threshold: float = 0.7
    # Optional metadata kept for the report.
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evaluators")
    @classmethod
    def _at_least_one_evaluator(cls, v: list[EvaluatorSpec]) -> list[EvaluatorSpec]:
        if not v:
            raise ValueError(
                "Each test case must define at least one evaluator. "
                "Use type=exact for a simple equality check."
            )
        return v


TestCaseList = Union[list[TestCase], list[dict[str, Any]]]

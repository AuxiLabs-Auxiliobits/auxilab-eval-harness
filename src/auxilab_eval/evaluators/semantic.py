"""Local sentence-transformers semantic similarity evaluator.

Loads `all-MiniLM-L6-v2` lazily so the harness has no hard dependency on
torch/sentence-transformers unless the user actually runs a semantic check.
"""

from __future__ import annotations

import math
import os
from typing import Any, Optional

from auxilab_eval._utils import get_field, stringify
from auxilab_eval.evaluators.base import EvaluationResult, Evaluator
from auxilab_eval.schema import TestCase

# Cache loaded models so repeated test cases don't reload weights.
_MODEL_CACHE: dict[str, Any] = {}


def _load_model(name: str):
    if name in _MODEL_CACHE:
        return _MODEL_CACHE[name]
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:  # pragma: no cover - import-time guard
        raise ImportError(
            "Semantic evaluator requires `sentence-transformers`. "
            "Install with `pip install auxilab-eval[semantic]`."
        ) from exc
    model = SentenceTransformer(name)
    _MODEL_CACHE[name] = model
    return model


def _cosine(a, b) -> float:
    # Pure-Python cosine for two equal-length numeric sequences.
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SemanticSimilarityEvaluator(Evaluator):
    """Pass when cosine similarity(actual, expected) >= `threshold`.

    Default model: `all-MiniLM-L6-v2` (384-dim, ~80MB, runs on CPU).
    Override via `AUXILAB_EVAL_EMBED_MODEL` env var.
    """

    name = "semantic"
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, spec) -> None:
        super().__init__(spec)
        self._model_name = os.getenv("AUXILAB_EVAL_EMBED_MODEL", self.DEFAULT_MODEL)

    def evaluate(self, test_case: TestCase, output: Any) -> EvaluationResult:
        field = self.spec.field
        expected: Optional[str] = (
            self.spec.expected
            if self.spec.expected is not None
            else (test_case.expected.get(field) if field else None)
        )
        actual = stringify(get_field(output, field))
        ev_name = f"semantic:{field or '<root>'}"

        if expected is None:
            return EvaluationResult(
                evaluator=ev_name, passed=False, score=0.0,
                detail="No expected text provided for semantic comparison.",
                weight=self.spec.weight,
            )

        try:
            model = _load_model(self._model_name)
            embeddings = model.encode(
                [stringify(expected), actual], normalize_embeddings=True
            )
            # `embeddings` is either a numpy array or a list of lists.
            sim = _cosine(list(embeddings[0]), list(embeddings[1]))
        except Exception as exc:  # noqa: BLE001
            return EvaluationResult(
                evaluator=ev_name, passed=False, score=0.0,
                detail=f"Embedding error: {exc}",
                weight=self.spec.weight,
            )

        threshold = float(self.spec.threshold)
        # Map similarity in [-1, 1] to a [0, 1] score.
        score = max(0.0, min(1.0, (sim + 1) / 2))
        passed = sim >= threshold
        return EvaluationResult(
            evaluator=ev_name,
            passed=passed,
            score=score,
            detail=(
                f"Cosine similarity {sim:.3f} "
                f"({'>=' if passed else '<'} threshold {threshold:.2f})."
            ),
            breakdown={
                "similarity": float(sim),
                "threshold": threshold,
                "expected": expected,
                "actual": actual,
                "model": self._model_name,
            },
            weight=self.spec.weight,
        )

"""Built-in evaluators.

Each evaluator implements `Evaluator.evaluate(test_case, output) -> EvaluationResult`
and is selected via `EvaluatorSpec.type`. Use `get_evaluator(spec)` to obtain an
instance from a spec.
"""

from auxilab_eval.evaluators.base import Evaluator, EvaluationResult, get_evaluator
from auxilab_eval.evaluators.exact import ExactMatchEvaluator
from auxilab_eval.evaluators.regex import RegexEvaluator
from auxilab_eval.evaluators.json_schema import JsonSchemaEvaluator
from auxilab_eval.evaluators.semantic import SemanticSimilarityEvaluator
from auxilab_eval.evaluators.llm_judge import LLMJudgeEvaluator

__all__ = [
    "Evaluator",
    "EvaluationResult",
    "get_evaluator",
    "ExactMatchEvaluator",
    "RegexEvaluator",
    "JsonSchemaEvaluator",
    "SemanticSimilarityEvaluator",
    "LLMJudgeEvaluator",
]

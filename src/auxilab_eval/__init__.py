"""auxilab-eval — a lightweight, framework-agnostic evaluation harness for agentic AI."""

from auxilab_eval.harness import EvalHarness, EvalReport, TestCaseResult
from auxilab_eval.schema import (
    EvaluatorSpec,
    Rubric,
    TestCase,
)
from auxilab_eval.runners import (
    AgentRunner,
    HttpRunner,
    LangGraphRunner,
    PythonRunner,
)
from auxilab_eval.failure_analyser import FailureAnalyser, FailureReport
from auxilab_eval.loader import load_test_cases

__all__ = [
    "EvalHarness",
    "EvalReport",
    "TestCaseResult",
    "TestCase",
    "EvaluatorSpec",
    "Rubric",
    "AgentRunner",
    "PythonRunner",
    "LangGraphRunner",
    "HttpRunner",
    "FailureAnalyser",
    "FailureReport",
    "load_test_cases",
]

__version__ = "0.1.0"

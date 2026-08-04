"""Load test cases from YAML or JSON files (or in-memory dicts)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Union

import yaml

from auxilab_eval.schema import TestCase

PathLike = Union[str, Path]
TestCaseSource = Union[PathLike, list[dict[str, Any]], list[TestCase]]


def load_test_cases(source: TestCaseSource) -> list[TestCase]:
    """Load and validate a list of `TestCase` objects from a path or list.

    Supports:
        - .yaml / .yml file containing a list of test case mappings
        - .json file containing a list of test case mappings
        - In-memory list of dicts (each conforming to the TestCase schema)
        - In-memory list of TestCase instances (returned as-is)
    """
    if isinstance(source, (str, Path)):
        return _load_from_path(Path(source))

    if isinstance(source, list):
        return [_coerce(item) for item in source]

    raise TypeError(
        f"Unsupported test case source: {type(source).__name__}. "
        "Pass a path, a list of dicts, or a list of TestCase instances."
    )


def _load_from_path(path: Path) -> list[TestCase]:
    if not path.exists():
        raise FileNotFoundError(f"Test case file not found: {path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ValueError(
            f"Unsupported test case file format: {suffix}. "
            "Use .yaml, .yml or .json."
        )

    if not isinstance(data, list):
        raise ValueError(
            f"Test case file {path} must contain a list at the top level."
        )

    return [_coerce(item) for item in data]


def _coerce(item: Any) -> TestCase:
    if isinstance(item, TestCase):
        return item
    if isinstance(item, dict):
        return TestCase.model_validate(item)
    raise TypeError(
        f"Cannot coerce {type(item).__name__} to TestCase; expected dict."
    )


def dump_test_cases(cases: Iterable[TestCase], path: PathLike) -> None:
    """Persist a list of test cases back to YAML or JSON for round-tripping."""
    path = Path(path)
    payload = [c.model_dump(exclude_none=True) for c in cases]
    if path.suffix.lower() in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    elif path.suffix.lower() == ".json":
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported output format: {path.suffix}")

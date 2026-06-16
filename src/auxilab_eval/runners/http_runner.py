"""Run a containerised / remote agent over HTTP."""

from __future__ import annotations

import os
from typing import Any, Optional

import requests

from auxilab_eval.runners.base import AgentRunner


class HttpRunner(AgentRunner):
    """POST the input payload as JSON to a remote agent endpoint.

    The remote endpoint is expected to return a JSON body which becomes the
    agent output. Useful for evaluating agents wrapped in FastAPI/Flask
    services or running in containers.
    """

    def __init__(
        self,
        url: str,
        *,
        method: str = "POST",
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        name: str | None = None,
    ) -> None:
        if not url:
            raise ValueError("HttpRunner requires a non-empty URL.")
        self.url = url
        self.method = method.upper()
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.timeout = timeout or float(os.getenv("AUXILAB_EVAL_HTTP_TIMEOUT", "30"))
        self.name = name or f"http:{url}"

    def invoke(self, payload: dict[str, Any]) -> Any:
        response = requests.request(
            self.method,
            self.url,
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        # Best-effort: try JSON, fall back to raw text.
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}

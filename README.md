# auxilab-eval-harness

> A lightweight, framework-agnostic test harness for agentic AI workflows.
> Define expected inputs/outputs in YAML, run your agent, and get a pass/fail
> scorecard with structured failure analysis. Local-first, zero cloud lock-in.

`auxilab-eval-harness` is the **missing testing layer for agentic AI**. Drop it
into any agent project, define a few YAML test cases, and get:

- ✅ Pass / fail per test case with per-evaluator scoring
- 🧠 LLM-as-judge scoring against a custom rubric (Claude)
- 🔍 Automatic failure classification (Hallucination / Tool Call Error /
  Reasoning Error / Output Format Error / Incomplete Task / Unexpected
  Behaviour)
- 📊 HTML reports with Matplotlib charts + SQLite run-history trend
- 🧪 First-class **pytest** integration for CI pipelines

---

## Why?

Testing agentic systems is an unsolved problem. Agents can succeed at a task
in many valid ways or fail in subtle ways that are invisible to standard unit
tests. Existing eval frameworks are either proprietary, cloud-dependent, or
glued to a single orchestration framework (LangChain, etc).

`auxilab-eval-harness` is **framework-agnostic**: bring your own agent (Python
function, LangGraph runnable, or any HTTP endpoint) and the harness will
evaluate it.

---

## Installation

```bash
pip install auxilab-eval
```

Or from source:

```bash
git clone https://github.com/AuxiLabs-Auxiliobits/auxilab-eval-harness
cd auxilab-eval-harness
pip install -e .
```

Set your Anthropic API key (only required for LLM-judge and failure analyser):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

See `.env.example` for the full list of environment variables.

---

## Quickstart

### 1. Define test cases (`tests.yaml`)

```yaml
- id: ap_001
  description: Duplicate invoice should be flagged
  input:
    invoice_id: INV-1001
    amount: 1500.00
    vendor: Acme Corp
  expected:
    decision: flag_duplicate
  evaluators:
    - type: exact
      field: decision
    - type: llm_judge
      rubric:
        correctness: Did the agent correctly identify the duplicate?
        clarity: Is the explanation clear and professional?
      weights:
        correctness: 0.7
        clarity: 0.3
```

### 2. Wire your agent

```python
from auxilab_eval import EvalHarness, PythonRunner

def my_agent(payload: dict) -> dict:
    # ... your agent logic ...
    return {"decision": "flag_duplicate", "reason": "matches INV-1001"}

harness = EvalHarness(
    runner=PythonRunner(my_agent),
    test_cases="tests.yaml",
)
report = harness.run()
report.to_html("report.html")
print(f"Pass rate: {report.pass_rate:.0%}")
```

### 3. Run from the CLI

```bash
auxilab-eval run --tests tests.yaml --agent demo.my_agent --html report.html
```

### 4. Use in pytest

```python
# conftest.py
pytest_plugins = ["auxilab_eval.pytest_plugin"]
```

```python
# test_agent.py
def test_ap_agent(eval_harness):
    eval_harness.assert_passes("tests.yaml", agent=my_agent)
```

---

## Components

| Component         | Purpose                                                    |
| ----------------- | ---------------------------------------------------------- |
| `schema`          | Pydantic models for test cases / rubrics                   |
| `runners`         | `PythonRunner`, `LangGraphRunner`, `HttpRunner`            |
| `evaluators`      | `exact`, `regex`, `json_schema`, `semantic`, `llm_judge`   |
| `failure_analyser`| Claude-powered failure classification                      |
| `reporter`        | HTML / Matplotlib / SQLite history                         |
| `pytest_plugin`   | `eval_harness` fixture + `--auxilab-eval` flag             |

### Built-in evaluators

- **`exact`** — strict equality on a field
- **`regex`** — pattern match
- **`json_schema`** — validate against a JSON Schema
- **`semantic`** — local sentence-transformers (`all-MiniLM-L6-v2`), no API key
- **`llm_judge`** — Claude scores output against a per-criterion rubric and
  returns a structured JSON score with rationale

### Failure classifier

When a test case fails, the harness asks Claude to bucket the failure into
one of:

- `Hallucination`
- `Tool Call Error`
- `Reasoning Error`
- `Output Format Error`
- `Incomplete Task`
- `Unexpected Behaviour`

…and returns a structured report with the raw output for inspection.

---

## Demo

A full demo against a mock **AP Exception Handling Agent** lives under
[demo/](demo/):

```bash
python demo/demo.py                # CLI demo
python demo/demo.py --gradio       # interactive Gradio UI
```

10 ready-made YAML test cases live in
[demo/test_cases/ap_exception_tests.yaml](demo/test_cases/ap_exception_tests.yaml).

---

## Project structure

```
auxilab-eval-harness/
├── src/auxilab_eval/
│   ├── schema.py          # Pydantic test-case models
│   ├── loader.py          # YAML/JSON loading
│   ├── harness.py         # Orchestrator
│   ├── runners/           # Agent adapters
│   ├── evaluators/        # Eval strategies
│   ├── failure_analyser.py
│   ├── reporter/          # HTML / charts / SQLite
│   ├── pytest_plugin.py
│   └── cli.py
├── demo/                  # AP Exception Agent + 10 cases + Gradio UI
├── tests/                 # Unit + integration tests
└── pyproject.toml
```

---

## Development

```bash
pip install -e ".[dev]"
pytest                              # run unit tests
python demo/demo.py                 # run end-to-end demo
auxilab-eval --help                 # CLI
```

---

## License

MIT — see [LICENSE](LICENSE).

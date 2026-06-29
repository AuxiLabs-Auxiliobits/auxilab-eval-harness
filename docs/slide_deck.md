# auxilab-eval-harness — Slide Deck
### AuxiLab Hackathon Submission · 6 Slides

> **Convert to PPT/PDF**: Open this file in any Markdown-to-slides tool
> (e.g. [Marp](https://marp.app/), [Slidev](https://sli.dev/), Google Slides import, or paste into PowerPoint).

---

## Slide 1 — The Problem

**Title**: AI Agents Break in Production — We Can't See It Coming

**Problem statement**:
- Finance teams deploy AI agents (AP exception handling, payment runs) with little visibility into correctness
- No structured way to verify: "Did this agent do the right thing on this invoice?"
- Manual QA is slow, inconsistent, and doesn't scale
- Teams discover failures *after* a wrong payment has been made or an exception has been missed

**Key pain points**:
- No repeatable test suite for agent outputs
- No audit trail of what the agent decided and why
- No way to detect regressions when the agent model is updated
- Finance domain correctness is high-stakes — a missed duplicate invoice = real money lost

**Visual suggestion**: Split screen — left: confused finance analyst, right: a failed payment

---

## Slide 2 — What We Built

**Title**: `auxilab-eval-harness` — Evaluate AI Agents via CLI *or* Browser UI

**What it is**:
A lightweight, framework-agnostic test harness that lets you define YAML test cases, run them against any Python AI agent, and get structured reports — from the terminal *or* a point-and-click web interface.

**Core capabilities**:

| Capability | Detail |
|---|---|
| **Gradio Web UI** | Upload YAML, pick agent, click Run — no CLI knowledge needed |
| YAML test definitions | Declare inputs, expected outputs, and evaluation strategy in plain YAML |
| 5 evaluator types | `exact`, `regex`, `json_schema`, `semantic`, `llm_judge` |
| 3 output formats | Interactive HTML report (downloadable), JSON, CSV (Excel-ready) |
| Rich CLI | Colorized pass/fail output with latency tracking |
| History tracking | SQLite-backed run history for trend analysis |
| CI/CD ready | Exit codes 0/1/2 for pipeline integration |

**Two ways to run**:
- **Web UI**: `python app.py` → open http://127.0.0.1:7860
- **CLI**: `auxilab-eval run --tests my_tests.yaml --agent demo.agent:handle --html report.html`

**Tech stack**: Python 3.9+, Pydantic v2, Click, Gradio 6, Jinja2, Anthropic Claude (optional), sentence-transformers (optional)

**Visual suggestion**: Two-panel screenshot — left: Web UI in browser, right: CLI terminal output

---

## Slide 3 — Demo & Screenshots

**Title**: Two Ways to Run — Browser UI & CLI

---

### Path A — Web UI (no CLI needed)

**Steps**:
1. `python app.py` → open **http://127.0.0.1:7860**
2. Upload a `.yaml` test file (or click a built-in example)
3. Select agent from dropdown — description panel shows required input fields
4. Click **▶ Run Evaluation**
5. Download the HTML report with the **📥 Download** button

**Screenshot — Web UI**:
- Left panel: file upload + agent dropdown + agent description
- Right panel: 🟢 summary card (pass rate, score, latency) + results table
- Each row: Test ID | ✅ PASS / ❌ FAIL | Score | Duration | Failure type
- Expandable full JSON output section
- Error messages shown inline for bad YAML, wrong agent, mismatched test file

---

### Path B — CLI (power users & CI/CD)

```
╔══════════════════════════════════════════╗
║  Evaluation Complete                     ║
╚══════════════════════════════════════════╝
  ✓ Passed:  18/20    Pass Rate: 🟢 90.0%
  Avg Latency: 12.4 ms
```

```bash
auxilab-eval run \
  --tests demo/test_cases/ap_exception_tests.yaml \
  --agent demo.ap_exception_agent:handle_ap_exception \
  --html report.html --csv results.csv
```

**Visual suggestion**: Side-by-side screenshot — browser UI on left, terminal on right

---

## Slide 4 — Results

**Title**: 38 Tests, 2 Agents, Full Coverage

**Test coverage**:

| Agent | Tests | Categories |
|---|---|---|
| AP Exception Handler | 20 | Duplicate detection, vendor validation, PO requirements, date logic, edge cases, security regression |
| Payment Run Agent | 18 | Happy path, early-pay discounts, fraud detection, watchlist blocking, cash constraints, edge cases |
| **Total** | **38** | Correctness, schema, semantic, regression, security |

**Evaluation strategy breakdown**:
- `exact` — 28 evaluators (correctness of decisions)
- `regex` — 18 evaluators (flexible reason/explanation matching)
- `json_schema` — 4 evaluators (output structure validation)
- `llm_judge` — 2 evaluators (reasoning quality scored by Claude)
- `semantic` — 1 evaluator (meaning similarity check)

**Performance** (on test machine):
- AP Exception: avg 12ms / test
- Payment Run: avg 15ms / test
- Full 38-test suite: < 1 second (excludes LLM-judge calls)

**Visual suggestion**: Bar chart — pass rates per category, or a 2×2 grid of metric cards

---

## Slide 5 — What's Next

**Title**: Roadmap — From Hackathon to Production

**Shipped in this submission ✅**:
- Web UI (Gradio) — upload YAML, select agent, download HTML report
- 38 YAML test cases across 2 Finance agents
- 5 evaluator types including LLM-as-judge (Claude)
- Interactive HTML reports + CSV + JSON export

**Immediate next steps (v0.2)**:
- [ ] Parallel test execution (asyncio runner) for large suites
- [ ] GitHub Actions workflow template (pre-built CI yaml)
- [ ] Threshold alerts: notify Slack/email when pass rate drops below threshold
- [ ] UI: side-by-side run comparison ("did this agent regress vs last run?")

**Medium term (v0.3)**:
- [ ] LangGraph agent runner (native integration with graph-based agents)
- [ ] Team dashboard: shared history DB for multiple agents/teams
- [ ] OpenAI and other LLM judge backends (not just Claude)
- [ ] UI: upload custom agent Python file directly in browser

**Long term vision**:
- Self-healing test generation — Claude writes new test cases from failure patterns
- Agent monitoring in production (not just dev/test) — integrate with logging pipelines
- Finance domain packs — pre-built test suites for AP, AR, GL, reconciliation agents

**Call to action**:
> Any team building AI agents in Finance needs structured evaluation.
> `python app.py` and run your first evaluation in under 2 minutes.

**Visual suggestion**: "Shipped / Next / Future" three-column layout

---

## Appendix — Technical Deep Dive

### Evaluator Pipeline

```
TestCase(input, expected, evaluators)
        │
        ▼
  PythonRunner.run(input)  ──→  actual_output: dict
        │
        ▼
  for evaluator in evaluators:
    score = evaluator.evaluate(actual_output, expected)
    weight = evaluator.weight
        │
        ▼
  weighted_average_score → PASS (≥0.75) or FAIL
```

### Supported Runners

| Runner | Use Case |
|---|---|
| `PythonRunner` | Any `callable(dict) → dict` Python function |
| `HttpRunner` | REST API endpoint — POST with JSON body |
| `LangGraphRunner` | LangGraph `CompiledGraph` objects |

### Key files

- `src/auxilab_eval/harness.py` — orchestrates the full run pipeline
- `src/auxilab_eval/schema.py` — Pydantic models for test cases and results
- `src/auxilab_eval/evaluators/` — one file per evaluator strategy
- `src/auxilab_eval/reporter/` — HTML (Jinja2), JSON, CSV, SQLite
- `demo/test_cases/*.yaml` — 38 ready-to-run test cases

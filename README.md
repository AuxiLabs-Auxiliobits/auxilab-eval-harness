# 🏆 auxilab-eval-harness: Production-Grade Evaluation Framework

**Status**: ✅ Competition-Ready | **Tests**: 38 | **Exports**: 3 formats | **Documentation**: Complete | **Slide Deck**: [`docs/slide_deck.md`](docs/slide_deck.md)

Transform your AI agents into production-grade systems with comprehensive evaluation, beautiful reports, and rich analytics.

---

## ⚡ Quick Start (Choose Your Speed)

### 🖱️ Easiest: Web UI (no CLI knowledge needed)
```bash
pip install -e .
pip install -r requirements.txt
python app.py
```
Then open **http://127.0.0.1:7860** in your browser.
Upload a YAML test file, pick an agent, click **Run Evaluation** — done.

### 🚀 Fastest: See Everything via CLI (1 minute)
```bash
python demo_all_features.py
```
Shows colourised CLI output, runs all 38 tests, generates HTML reports and CSV exports.

### 📖 Quick: CLI Commands (5 minutes)
```bash
# Run AP Exception tests
auxilab-eval run \
  --tests demo/test_cases/ap_exception_tests.yaml \
  --agent demo.ap_exception_agent:handle_ap_exception \
  --html report.html

# Run Payment Run tests
auxilab-eval run \
  --tests demo/test_cases/payment_run_tests.yaml \
  --agent demo.payment_run_agent:run_payment \
  --html report.html
```

### 🎬 Full Setup
```bash
# Install package
pip install -e .

# Install dependencies
pip install -r requirements.txt

# Run demo
python demo_all_features.py

# View history
auxilab-eval history --limit 20
```

---

## 🖥️ Web UI — Interactive Evaluation

The web UI lets you evaluate any agent through a browser — no terminal commands required.

### Starting the UI

```bash
# Make sure dependencies are installed
pip install -e .
pip install -r requirements.txt

# Launch the server
python app.py
```

Open **http://127.0.0.1:7860** in Chrome or Edge.

> **Tip for VS Code users**: Do not click the link in the terminal (it opens VS Code's built-in browser).
> Copy the URL and paste it directly into Chrome or Edge.

### How to use it

**Step 1 — Upload your test cases**

Click the upload box and attach any `.yaml` or `.yml` test case file.
Use the built-in examples in `demo/test_cases/` to get started:
- `demo/test_cases/ap_exception_tests.yaml` — 20 AP Exception tests
- `demo/test_cases/payment_run_tests.yaml` — 18 Payment Run tests

**Step 2 — Select an agent**

Pick from the dropdown:
| Agent | Description |
|---|---|
| AP Exception Handler | Classifies invoice exceptions: approve, flag_duplicate, needs_review, reject |
| Payment Run Agent | Processes payment decisions: pay_now, hold, split_payment, defer, reject |

The agent description panel shows required and optional input fields so you know which test file to pair with it.

**Step 3 — Run**

Click **▶ Run Evaluation**. Results appear immediately:
- **Summary card** — pass rate, average score, latency, run ID
- **📥 Download HTML Report** — button appears after a successful run; click it to save the full interactive HTML report to your machine
- **Results table** — one row per test: ID, description, ✅ PASS / ❌ FAIL, score, duration, failure type
- **Full JSON output** — expandable section with complete detail for every test case

### Error handling

The UI validates your input before running and gives clear error messages:

| Problem | Message shown |
|---|---|
| No file uploaded | "No file uploaded" |
| Wrong file type (e.g. `.txt`) | "Wrong file type: `.txt`" |
| Broken YAML syntax | YAML parse error with line/column |
| YAML is not a list | "Wrong structure" with example |
| Test case missing `id`/`input`/`expected` | Lists each broken item by name |
| No agent selected | "No agent selected" + lists available agents |
| Wrong agent for the test file | "Agent/test case mismatch" with tip |
| Any runtime exception | Full traceback in a code block |

### Writing your own test cases for the UI

Create a `.yaml` file anywhere on your machine following this format:

```yaml
- id: my_001_duplicate
  description: Block duplicate invoices
  tags: [custom]
  input:
    invoice_id: INV-9999
    amount: 12000.00
    vendor: Acme Corp
    po_number: PO-55
    due_date: "2026-08-01"
    duplicate_of: INV-9998
  expected:
    decision: flag_duplicate
  evaluators:
    - type: exact
      field: decision
    - type: regex
      field: reason
      pattern: "(?i)duplicate"
```

Upload it via the UI, select the matching agent, and run.

---

## 🎯 What Is This?

`auxilab-eval-harness` is a **production-grade evaluation framework** for testing AI agents with:

- ✅ **38 Comprehensive Test Cases** (doubled from 20)
- ✅ **Multiple Evaluation Strategies** (exact, regex, JSON schema, semantic, LLM-as-judge)
- ✅ **Professional HTML Reports** with interactive features
- ✅ **Rich CLI Output** with beautiful formatting
- ✅ **Multiple Export Formats** (HTML, JSON, CSV)
- ✅ **Performance Analytics** (latency tracking, metrics)
- ✅ **Security-Focused Testing** with regression tests

Perfect for evaluating AI agents before production deployment.

---

## 📊 Features Overview

### Test Coverage Matrix

**AP Exception Agent — 20 tests:** Correctness (6), Schema validation (3), Quality (3), Edge cases (5), Regression (3) — covering duplicate detection, unknown vendors, missing/empty PO, thresholds, dates, decimal precision, case/whitespace normalization, confidence scoring, and strategic-vendor regression.

**Payment Run Agent — 18 tests:** Core logic (6), Cash management (3), Quality (2), Edge cases (7) — covering happy path, early-pay discounts, past-due priority, watchlist holds, fraud scoring, cash-constrained splits, schema contracts, and a security regression for small watchlisted amounts.

### Evaluation Strategies

Your harness uses **5 different evaluation methods**:

1. **Exact Matching**: Direct string comparison
2. **Regex Patterns**: Pattern-based matching for flexible validation
3. **JSON Schema**: Validate data structure and types
4. **Semantic Similarity**: Using sentence-transformers for meaning-based comparison
5. **LLM-as-Judge**: Claude-based evaluation for complex reasoning

---

## 🚀 Running Tests

### Run All Tests (Demo)
```bash
python demo_all_features.py
```
Runs both agents, generates all reports, shows everything.

### Run Specific Agent

**AP Exception Agent**:
```bash
auxilab-eval run \
  --tests demo/test_cases/ap_exception_tests.yaml \
  --agent demo.ap_exception_agent:handle_ap_exception \
  --html ap_report.html \
  --csv ap_results.csv
```

**Payment Run Agent**:
```bash
auxilab-eval run \
  --tests demo/test_cases/payment_run_tests.yaml \
  --agent demo.payment_run_agent:run_payment \
  --html pr_report.html \
  --csv pr_results.csv
```

### View Results

**HTML Report** (Interactive):
```bash
# Open the HTML file in your browser
open ap_report.html  # Mac
start ap_report.html # Windows
```

**CSV Export** (Spreadsheet):
```bash
# Open in Excel or your preferred spreadsheet tool
python -c "import pandas as pd; print(pd.read_csv('ap_results.csv'))"
```

**History**:
```bash
export AUXILAB_EVAL_DB=~/.auxilab/history.db
auxilab-eval history --limit 10
```

---

## 📊 Performance

Typical latencies:
- **AP Exception**: 10-15ms per test
- **Payment Run**: 12-18ms per test
- **Report Generation**: <500ms for HTML/CSV

---

## 📁 Project Structure

```
auxilab-eval-harness/
├── src/auxilab_eval/
│   ├── evaluators/          # exact, regex, json_schema, semantic, llm_judge
│   ├── runners/             # python, http, langgraph
│   ├── reporter/            # HTML template, charts, SQLite history store
│   ├── cli.py               # Rich CLI with colors
│   ├── harness.py           # Core orchestrator + CSV export
│   ├── loader.py            # YAML/JSON loading
│   ├── schema.py            # Pydantic test-case models
│   └── _utils.py
├── demo/                    # AP Exception + Payment Run agents + test cases
├── tests/                   # Unit + integration tests
├── reports/                 # Generated HTML/CSV reports
├── demo_all_features.py     # Run this to see everything
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- pip

### Install

1. **Clone/Download**:
   ```bash
   cd auxilab-eval-harness
   ```

2. **Install Package** (editable mode):
   ```bash
   pip install -e .
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Installation**:
   ```bash
   python -m auxilab_eval.cli --version
   # Output: auxilab-eval, version 0.1.0
   ```

### Dependencies

- **Core**: Pydantic 2.0+, PyYAML, Click
- **Evaluation**: sentence-transformers, anthropic (Claude for LLM judge)
- **Reporting**: Jinja2, matplotlib
- **Agents**: LangGraph (optional)

---

## 🎯 Evaluator Examples

### Multiple Evaluators

Flexibly choose how to evaluate each test:

1. **exact**: Exact string matching
   ```yaml
   expected: "DUPLICATE"
   evaluator: exact
   ```

2. **regex**: Pattern matching
   ```yaml
   expected: "DUPLICATE|HOLD"
   evaluator: regex
   ```

3. **json_schema**: Structure validation
   ```yaml
   expected:
     type: object
     required: [duplicate, confidence]
   evaluator: json_schema
   ```

4. **semantic**: Meaning-based (uses embeddings)
   ```yaml
   expected: "This invoice is a duplicate"
   evaluator: semantic
   ```

5. **llm_judge**: AI evaluation (uses Claude)
   ```yaml
   expected: "Agent correctly identifies fraud with high confidence"
   evaluator: llm_judge
   ```

---

## 🛡️ Security & Quality

### Security Testing
Your harness includes security-focused tests:
- Watchlist bypass detection
- Fraud threshold validation
- Malformed input handling
- Edge case protection

### Quality Metrics
Tests evaluate:
- **Correctness**: Does the agent produce right answer?
- **Schema Compliance**: Is output properly structured?
- **Semantic Accuracy**: Is the reasoning sound?
- **Performance**: How fast is the response?
- **Consistency**: Are results repeatable?

### Regression Prevention
Includes specific tests for:
- Known bugs to prevent reoccurrence
- Past vulnerabilities
- Common failure patterns
- Edge case regressions

---

## 🚨 Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'auxilab_eval'` | `pip install -e .` |
| `ImportError: cannot import name 'EvalHarness'` | `pip install -e . --force-reinstall` |
| `No module named 'anthropic'` (or similar) | `pip install -r requirements.txt` |
| `command not found: auxilab-eval` | Use the module: `python -m auxilab_eval.cli run --help` |
| HTML report not generating | `pip install jinja2 matplotlib` |

---

## 📖 API Usage (Python)

### Programmatic Usage

```python
from auxilab_eval.harness import EvalHarness
from auxilab_eval.runners import PythonRunner
from auxilab_eval.evaluators import ExactEvaluator

# Create harness
harness = EvalHarness()

# Add runner
runner = PythonRunner()
harness.add_runner("my_agent", my_agent_function)

# Add evaluator
evaluator = ExactEvaluator()

# Load tests
tests = harness.load_tests("path/to/tests.yaml")

# Run evaluation
report = harness.run_evaluation(tests, runner, evaluator)

# Generate outputs
report.to_html("report.html")
report.to_csv("results.csv")
report.to_json("results.json")

# Print summary
print(f"Pass Rate: {report.pass_rate:.1%}")
print(f"Avg Score: {report.average_score:.2f}")
```

### Test Result Access

```python
for result in report.test_results:
    print(f"{result.test_id}: {result.status}")
    print(f"  Score: {result.score}")
    print(f"  Duration: {result.duration_ms}ms")
    if result.failure_info:
        print(f"  Failure: {result.failure_info.failure_type}")
```

---

## 📊 Understanding Results

### Pass Rate Interpretation

- **🟢 100%**: All tests passed perfectly
- **🟡 90-99%**: Tests mostly passed, minor issues
- **🟡 75-89%**: Some tests failed, issues to address
- **🔴 <75%**: Many tests failed, significant problems

### Score Breakdown

Each test gets a score (0-1):
- **1.0**: Perfect match
- **0.9-0.99**: Minor deviation
- **0.75-0.89**: Significant deviation but acceptable
- **<0.75**: Major deviation, test failed

### Latency Analysis

Watch latency to catch performance issues:
- **<10ms**: Excellent
- **10-20ms**: Good
- **20-50ms**: Acceptable
- **>50ms**: Investigate

---

## 🔗 Integration

### CI/CD Integration

Use exit codes for automation:

```bash
auxilab-eval run \
  --tests tests.yaml \
  --agent my_agent:handle \
  --html report.html

# Exit codes:
# 0 = All tests passed
# 1 = Some tests failed
# 2 = Error running tests
```

### GitHub Actions

```yaml
- name: Run Evaluations
  run: python demo_all_features.py

- name: Check Results
  run: |
    if grep -q "FAIL" reports/results.csv; then
      exit 1
    fi
```

### Slack Notifications

```python
# After running tests
report = harness.run_evaluation(...)
if report.pass_rate < 0.9:
    notify_slack(f"Tests failing: {report.pass_rate:.1%}")
```

---

## ⚠️ Known Limitations

- **LLM-judge evaluator requires an Anthropic API key** — tests using `llm_judge` are skipped if `ANTHROPIC_API_KEY` is not set
- **Semantic evaluator downloads a model on first use** — `sentence-transformers` pulls ~90 MB on first run; subsequent runs are offline
- **No built-in parallelism** — test cases execute sequentially; large suites (100+) may be slow
- **HTTP runner requires a live endpoint** — `http_runner` tests will fail if the target service is not running
- **LangGraph runner requires LangGraph 0.2+** — older LangGraph versions are not supported
- **History database is local only** — `.auxilab_eval/history.sqlite` is not shared across machines
- **Report charts require matplotlib** — if omitted, HTML reports render without charts but are otherwise fully functional
- **Python 3.9+ only** — f-strings and `match` syntax used internally; Python 3.8 is not supported despite pyproject classifier

---

## 🎬 Demo Video

> **Watch the 3-minute end-to-end demo:**
> 🔗 [https://drive.google.com/drive/folders/1Pl8t-bwD3HcQUp2qd5AZBLtiApMf1384](https://drive.google.com/drive/folders/1Pl8t-bwD3HcQUp2qd5AZBLtiApMf1384)

The video covers:
1. Installing the harness with `pip install -e .`
2. Running `python demo_all_features.py`
3. Viewing the interactive HTML report in a browser
4. Running a custom test case from the CLI

---

## 📞 Support & Help

### Common Questions

**Q: How do I add my own tests?**
A: Create a YAML file in `demo/test_cases/` following the format in existing files.

**Q: Can I use different evaluators?**
A: Yes! Mix evaluators by setting the `evaluator` field per test.

**Q: How do I evaluate my own agent?**
A: Implement a function and pass it via `--agent module:function`.

**Q: Can I export to other formats?**
A: Currently: HTML, JSON, CSV. Custom exporters can be added.

**Q: How are results stored?**
A: Results cached in `~/.auxilab/history.db` with history tracking.

---

## 📄 License

See [LICENSE](LICENSE) file for details.


---

## Built By

| Name | GitHub |
|------|--------|
| Shubham Negi | [@shubhamnegi-ux](https://github.com/shubhamnegi-ux) |
| Nikhil Verma | [@vermaniks](https://github.com/vermaniks) |

Built during the **AuxiLab Founding Hackathon** by [Auxiliobits Technologies](https://auxiliobits.com) · [AuxiLab Catalogue](https://auxiliobits.com/auxilab)

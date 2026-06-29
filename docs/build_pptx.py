"""
Generate docs/auxilab_eval_harness.pptx from the slide deck content.
Run: python docs/build_pptx.py
Requires: pip install python-pptx
"""
import subprocess, sys, os

# Auto-install if missing
try:
    from pptx import Presentation
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-pptx"])
    from pptx import Presentation

from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

_DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Palette ──────────────────────────────────────────────────────────────────
DARK_BG    = RGBColor(0x0D, 0x1B, 0x2A)   # near-black navy
ACCENT     = RGBColor(0x00, 0xD4, 0xFF)   # cyan-blue
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xCC, 0xDD, 0xEE)
YELLOW     = RGBColor(0xFF, 0xD7, 0x00)
GREEN      = RGBColor(0x00, 0xE5, 0x76)
SLIDE_W    = Inches(13.33)
SLIDE_H    = Inches(7.5)

# ── Helpers ───────────────────────────────────────────────────────────────────

def new_prs():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    blank_layout = prs.slide_layouts[6]   # truly blank
    return prs.slides.add_slide(blank_layout)


def fill_bg(slide, color: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, l, t, w, h, color: RGBColor, alpha=None):
    shape = slide.shapes.add_shape(1, l, t, w, h)  # MSO_SHAPE_TYPE.RECTANGLE
    shape.line.fill.background()
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    return shape


def add_label(slide, text, l, t, w, h,
              font_size=18, bold=False, color=WHITE,
              align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(l, t, w, h)
    txb.word_wrap = wrap
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txb


def add_para(tf, text, font_size=16, bold=False, color=WHITE,
             align=PP_ALIGN.LEFT, space_before=6):
    from pptx.util import Pt as _Pt
    p = tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    run = p.add_run()
    run.text = text
    run.font.size = _Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return p


def slide_header(slide, title, subtitle=None):
    """Dark top bar with title."""
    add_rect(slide, 0, 0, SLIDE_W, Inches(1.35), DARK_BG)
    # accent bar
    add_rect(slide, 0, Inches(1.35), SLIDE_W, Pt(4), ACCENT)
    add_label(slide, title,
              Inches(0.4), Inches(0.15),
              Inches(12.5), Inches(0.9),
              font_size=32, bold=True, color=WHITE)
    if subtitle:
        add_label(slide, subtitle,
                  Inches(0.4), Inches(0.9),
                  Inches(12.5), Inches(0.45),
                  font_size=16, color=ACCENT)


def bullet_box(slide, items, l, t, w, h,
               font_size=16, bullet="▸ ", color=WHITE):
    txb = slide.shapes.add_textbox(l, t, w, h)
    txb.word_wrap = True
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(4)
        run = p.add_run()
        run.text = f"{bullet}{item}"
        run.font.size = Pt(font_size)
        run.font.color.rgb = color
    return txb


def table_box(slide, headers, rows, l, t, w, h):
    """Simple coloured table."""
    rows_count = len(rows) + 1
    cols_count = len(headers)
    tbl = slide.shapes.add_table(rows_count, cols_count, l, t, w, h).table
    col_w = w // cols_count
    for i in range(cols_count):
        tbl.columns[i].width = col_w

    def style_cell(cell, text, bg, fg=WHITE, bold=False, sz=13):
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.runs[0] if p.runs else p.add_run()
        run.text = text
        run.font.size = Pt(sz)
        run.font.bold = bold
        run.font.color.rgb = fg

    HDR_BG = RGBColor(0x00, 0x56, 0x8C)
    ROW_BG = RGBColor(0x1A, 0x2E, 0x44)
    ALT_BG = RGBColor(0x14, 0x25, 0x38)

    for ci, h in enumerate(headers):
        style_cell(tbl.cell(0, ci), h, HDR_BG, WHITE, bold=True, sz=13)
    for ri, row in enumerate(rows):
        bg = ROW_BG if ri % 2 == 0 else ALT_BG
        for ci, val in enumerate(row):
            style_cell(tbl.cell(ri + 1, ci), str(val), bg, LIGHT_GREY, sz=12)
    return tbl


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title / Problem
# ═══════════════════════════════════════════════════════════════════════════════

def make_slide1(prs):
    slide = blank_slide(prs)
    fill_bg(slide, DARK_BG)

    # full-width accent stripe at bottom
    add_rect(slide, 0, SLIDE_H - Inches(0.08), SLIDE_W, Inches(0.08), ACCENT)

    # Big title block
    add_rect(slide, 0, 0, SLIDE_W, Inches(3.0), RGBColor(0x05, 0x10, 0x20))
    add_label(slide,
              "AI Agents Break in Production —\nWe Can't See It Coming",
              Inches(0.5), Inches(0.3), Inches(12.3), Inches(2.2),
              font_size=36, bold=True, color=WHITE)
    add_label(slide,
              "auxilab-eval-harness  ·  AuxiLab Hackathon 2026",
              Inches(0.5), Inches(2.4), Inches(12.3), Inches(0.5),
              font_size=18, color=ACCENT)

    # accent divider
    add_rect(slide, 0, Inches(3.0), SLIDE_W, Pt(3), ACCENT)

    # Two-column bullets
    left_items = [
        "Finance teams deploy AI agents with no visibility into correctness",
        "No repeatable way to verify: 'Did the agent decide correctly?'",
        "Manual QA is slow, inconsistent, and doesn't scale",
    ]
    right_items = [
        "No audit trail — what did the agent decide, and why?",
        "Regressions surface only after a wrong payment is made",
        "Finance is high-stakes: 1 missed duplicate = real money lost",
    ]

    add_label(slide, "The Problem", Inches(0.5), Inches(3.15),
              Inches(5.8), Inches(0.4), font_size=15, bold=True, color=ACCENT)
    bullet_box(slide, left_items, Inches(0.5), Inches(3.6),
               Inches(5.8), Inches(3.0), font_size=15)

    add_label(slide, "Key Pain Points", Inches(7.0), Inches(3.15),
              Inches(5.8), Inches(0.4), font_size=15, bold=True, color=YELLOW)
    bullet_box(slide, right_items, Inches(7.0), Inches(3.6),
               Inches(5.8), Inches(3.0), font_size=15, color=LIGHT_GREY)

    # vertical divider
    add_rect(slide, Inches(6.6), Inches(3.1), Pt(2), Inches(4.2), ACCENT)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — What We Built
# ═══════════════════════════════════════════════════════════════════════════════

def make_slide2(prs):
    slide = blank_slide(prs)
    fill_bg(slide, DARK_BG)
    slide_header(slide,
                 "What We Built",
                 "auxilab-eval-harness — Evaluate AI Agents via CLI or Browser UI")

    # Tagline
    add_label(slide,
              "Define YAML test cases → run against any Python agent → get structured reports — CLI or browser.",
              Inches(0.4), Inches(1.5), Inches(12.5), Inches(0.45),
              font_size=16, color=LIGHT_GREY)

    # Capabilities table
    headers = ["Capability", "Detail"]
    rows = [
        ["Gradio Web UI",       "Upload YAML, pick agent, click Run — no CLI needed. Download HTML report."],
        ["YAML test definitions", "Inputs, expected outputs & eval strategy in plain YAML"],
        ["5 evaluator types",   "exact · regex · json_schema · semantic · llm_judge"],
        ["3 export formats",    "Interactive HTML report · JSON · CSV (Excel-ready)"],
        ["Rich CLI",            "Colorized pass/fail output with latency & score tracking"],
        ["CI/CD ready",         "Exit codes 0 / 1 / 2 — drop straight into GitHub Actions"],
    ]
    table_box(slide, headers, rows,
              Inches(0.4), Inches(2.1),
              Inches(9.5), Inches(4.8))

    # Tech stack pill
    add_rect(slide, Inches(10.1), Inches(2.1), Inches(3.0), Inches(4.8),
             RGBColor(0x05, 0x18, 0x2E))
    add_label(slide, "Tech Stack", Inches(10.2), Inches(2.2),
              Inches(2.8), Inches(0.4), font_size=13, bold=True, color=ACCENT)
    stack = ["Python 3.9+", "Pydantic v2", "Click", "Gradio 6",
             "Jinja2", "Anthropic Claude*", "sentence-transformers*", "", "* optional"]
    bullet_box(slide, stack, Inches(10.2), Inches(2.65),
               Inches(2.8), Inches(4.0), font_size=13, bullet="· ")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Demo
# ═══════════════════════════════════════════════════════════════════════════════

def make_slide3(prs):
    slide = blank_slide(prs)
    fill_bg(slide, DARK_BG)
    slide_header(slide, "Demo — Two Ways to Run", "Browser UI (no CLI needed)  |  CLI for power users & CI/CD")

    # vertical divider
    add_rect(slide, Inches(6.55), Inches(1.5), Pt(2), Inches(5.7), ACCENT)

    # ── LEFT: Web UI panel ────────────────────────────────────────────────────
    add_label(slide, "🖼️  Path A — Web UI",
              Inches(0.3), Inches(1.55), Inches(6.0), Inches(0.4),
              font_size=15, bold=True, color=ACCENT)

    ui_steps = [
        "1.  python app.py",
        "      Opens http://127.0.0.1:7860",
        "",
        "2.  Upload .yaml test file",
        "      or click a built-in example",
        "",
        "3.  Select agent from dropdown",
        "      Description shows required fields",
        "",
        "4.  Click  ▶ Run Evaluation",
        "",
        "5.  📥 Download HTML Report button",
        "      Same interactive report as CLI",
    ]
    bullet_box(slide, ui_steps, Inches(0.3), Inches(2.05),
               Inches(6.0), Inches(5.1), font_size=13, bullet="")

    # ── RIGHT: CLI panel ───────────────────────────────────────────────────────
    add_label(slide, "🖥️  Path B — CLI",
              Inches(6.75), Inches(1.55), Inches(6.3), Inches(0.4),
              font_size=15, bold=True, color=YELLOW)

    add_rect(slide, Inches(6.75), Inches(2.05), Inches(6.3), Inches(2.1),
             RGBColor(0x05, 0x12, 0x22))
    cli_box = slide.shapes.add_textbox(Inches(6.85), Inches(2.1),
                                       Inches(6.1), Inches(2.0))
    tf = cli_box.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = (
        "╔════════════════════════════════╗\n"
        "║  Evaluation Complete           ║\n"
        "╚════════════════════════════════╝\n"
        "  ✓ Passed:  18/20  🟢 90.0%\n"
        "  Avg Latency: 12.4 ms"
    )
    run.font.size = Pt(11)
    run.font.color.rgb = GREEN
    run.font.name = "Courier New"

    add_label(slide, "Command:",
              Inches(6.75), Inches(4.3), Inches(6.3), Inches(0.35),
              font_size=13, bold=True, color=ACCENT)
    add_rect(slide, Inches(6.75), Inches(4.65), Inches(6.3), Inches(1.5),
             RGBColor(0x05, 0x12, 0x22))
    cmd_box = slide.shapes.add_textbox(Inches(6.85), Inches(4.7),
                                       Inches(6.1), Inches(1.4))
    tf2 = cmd_box.text_frame
    p2 = tf2.paragraphs[0]
    r2 = p2.add_run()
    r2.text = (
        "auxilab-eval run \\\n"
        "  --tests ap_tests.yaml \\\n"
        "  --agent demo.agent:handle \\\n"
        "  --html report.html"
    )
    r2.font.size = Pt(11)
    r2.font.color.rgb = LIGHT_GREY
    r2.font.name = "Courier New"


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Results
# ═══════════════════════════════════════════════════════════════════════════════

def make_slide4(prs):
    slide = blank_slide(prs)
    fill_bg(slide, DARK_BG)
    slide_header(slide, "Results", "38 Tests · 2 Agents · Full Evaluation Coverage")

    # Coverage table
    add_label(slide, "Test Coverage",
              Inches(0.4), Inches(1.55), Inches(8.5), Inches(0.35),
              font_size=14, bold=True, color=ACCENT)

    cov_headers = ["Agent", "Tests", "Categories"]
    cov_rows = [
        ["AP Exception Handler", "20",
         "Duplicate, vendor, PO, dates, edge cases, security"],
        ["Payment Run Agent",    "18",
         "Happy path, discounts, fraud, watchlist, cash, edge cases"],
        ["Total",               "38",
         "Correctness · Schema · Semantic · Regression · Security"],
    ]
    table_box(slide, cov_headers, cov_rows,
              Inches(0.4), Inches(1.95), Inches(8.5), Inches(2.0))

    # Evaluator breakdown
    add_label(slide, "Evaluator Breakdown",
              Inches(0.4), Inches(4.1), Inches(8.5), Inches(0.35),
              font_size=14, bold=True, color=YELLOW)

    eval_headers = ["Type", "Count", "Purpose"]
    eval_rows = [
        ["exact",       "28", "Strict field equality — correctness of decisions"],
        ["regex",       "18", "Pattern matching — flexible reason/explanation checks"],
        ["json_schema",  "4", "Output structure & type validation"],
        ["llm_judge",    "2", "Claude scores reasoning quality"],
        ["semantic",     "1", "Meaning similarity via sentence-transformers"],
    ]
    table_box(slide, eval_headers, eval_rows,
              Inches(0.4), Inches(4.5), Inches(8.5), Inches(2.7))

    # Performance card
    add_rect(slide, Inches(9.1), Inches(1.55), Inches(3.8), Inches(5.65),
             RGBColor(0x05, 0x18, 0x2E))
    add_label(slide, "Performance",
              Inches(9.25), Inches(1.65), Inches(3.4), Inches(0.4),
              font_size=14, bold=True, color=ACCENT)
    perf = [
        "AP Exception",
        "  avg 12 ms / test",
        "",
        "Payment Run",
        "  avg 15 ms / test",
        "",
        "Full 38-test suite",
        "  < 1 second",
        "  (excl. LLM-judge)",
        "",
        "Pass Rate",
        "  🟢 90 %+",
    ]
    bullet_box(slide, perf, Inches(9.25), Inches(2.1),
               Inches(3.4), Inches(4.8), font_size=14, bullet="")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — What's Next
# ═══════════════════════════════════════════════════════════════════════════════

def make_slide5(prs):
    slide = blank_slide(prs)
    fill_bg(slide, DARK_BG)
    slide_header(slide, "What's Next", "Roadmap — From Hackathon to Production")

    COL_W = Inches(3.9)

    # NOW column
    add_rect(slide, Inches(0.3), Inches(1.55), COL_W, Inches(0.4),
             RGBColor(0x00, 0x56, 0x8C))
    add_label(slide, "  v0.2 — Next",
              Inches(0.3), Inches(1.55), COL_W, Inches(0.4),
              font_size=14, bold=True, color=WHITE)
    now_items = [
        "Parallel test execution (asyncio)",
        "GitHub Actions workflow template",
        "Slack / email threshold alerts",
        "UI: side-by-side run comparison",
    ]
    add_rect(slide, Inches(0.3), Inches(1.95), COL_W, Inches(2.6),
             RGBColor(0x0A, 0x1E, 0x35))
    bullet_box(slide, now_items, Inches(0.4), Inches(2.05),
               Inches(3.7), Inches(2.4), font_size=14)

    # NEXT column
    add_rect(slide, Inches(4.5), Inches(1.55), COL_W, Inches(0.4),
             RGBColor(0x00, 0x56, 0x4A))
    add_label(slide, "  v0.3 — Medium Term",
              Inches(4.5), Inches(1.55), COL_W, Inches(0.4),
              font_size=14, bold=True, color=WHITE)
    next_items = [
        "Native LangGraph runner",
        "Team dashboard with shared DB",
        "OpenAI & other LLM judge backends",
        "UI: upload agent .py directly",
    ]
    add_rect(slide, Inches(4.5), Inches(1.95), COL_W, Inches(2.6),
             RGBColor(0x08, 0x1E, 0x18))
    bullet_box(slide, next_items, Inches(4.6), Inches(2.05),
               Inches(3.7), Inches(2.4), font_size=14)

    # LATER column
    add_rect(slide, Inches(8.7), Inches(1.55), COL_W, Inches(0.4),
             RGBColor(0x56, 0x3B, 0x00))
    add_label(slide, "  Vision",
              Inches(8.7), Inches(1.55), COL_W, Inches(0.4),
              font_size=14, bold=True, color=WHITE)
    later_items = [
        "Self-healing test generation by Claude",
        "Production agent monitoring",
        "Finance domain test packs (AP/AR/GL)",
    ]
    add_rect(slide, Inches(8.7), Inches(1.95), COL_W, Inches(2.6),
             RGBColor(0x1E, 0x14, 0x04))
    bullet_box(slide, later_items, Inches(8.8), Inches(2.05),
               Inches(3.7), Inches(2.4), font_size=14)

    # Call to action banner
    add_rect(slide, 0, Inches(5.0), SLIDE_W, Inches(2.2),
             RGBColor(0x00, 0x3A, 0x5C))
    add_label(slide,
              "Any team building AI agents in Finance needs structured evaluation.",
              Inches(0.5), Inches(5.1), Inches(12.3), Inches(0.6),
              font_size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_label(slide,
              "python app.py   →   open http://127.0.0.1:7860   →   run your first evaluation in 2 minutes",
              Inches(0.5), Inches(5.75), Inches(12.3), Inches(0.55),
              font_size=17, color=ACCENT, align=PP_ALIGN.CENTER)
    add_label(slide,
              "github.com/AuxiLabs-Auxiliobits/auxilab-eval-harness",
              Inches(0.5), Inches(6.35), Inches(12.3), Inches(0.45),
              font_size=14, color=LIGHT_GREY, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Appendix / Architecture
# ═══════════════════════════════════════════════════════════════════════════════

def make_slide6(prs):
    slide = blank_slide(prs)
    fill_bg(slide, DARK_BG)
    slide_header(slide, "Appendix — Architecture & Key Files", "Technical Deep Dive")

    # Pipeline box
    add_label(slide, "Evaluation Pipeline",
              Inches(0.4), Inches(1.55), Inches(5.8), Inches(0.4),
              font_size=14, bold=True, color=ACCENT)
    pipeline = (
        "TestCase(input, expected, evaluators)\n"
        "         │\n"
        "         ▼\n"
        "  Runner.run(input)  ──►  actual_output\n"
        "         │\n"
        "         ▼\n"
        "  for evaluator in evaluators:\n"
        "    score = evaluator.evaluate(...)\n"
        "         │\n"
        "         ▼\n"
        "  weighted_avg_score\n"
        "  → PASS (≥ 0.75) or FAIL"
    )
    add_rect(slide, Inches(0.4), Inches(1.95), Inches(5.4), Inches(4.8),
             RGBColor(0x05, 0x12, 0x22))
    code_box = slide.shapes.add_textbox(Inches(0.55), Inches(2.05),
                                        Inches(5.1), Inches(4.6))
    tf = code_box.text_frame
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = pipeline
    r.font.size = Pt(12)
    r.font.color.rgb = GREEN
    r.font.name = "Courier New"

    # Runners table
    add_label(slide, "Supported Runners",
              Inches(6.2), Inches(1.55), Inches(6.7), Inches(0.4),
              font_size=14, bold=True, color=YELLOW)
    runner_headers = ["Runner", "Use Case"]
    runner_rows = [
        ["PythonRunner",    "Any callable(dict) → dict Python function"],
        ["HttpRunner",      "REST API endpoint — POST with JSON body"],
        ["LangGraphRunner", "LangGraph CompiledGraph objects"],
    ]
    table_box(slide, runner_headers, runner_rows,
              Inches(6.2), Inches(1.95), Inches(6.7), Inches(1.7))

    # Key files table
    add_label(slide, "Key Files",
              Inches(6.2), Inches(3.8), Inches(6.7), Inches(0.4),
              font_size=14, bold=True, color=ACCENT)
    file_headers = ["File", "Purpose"]
    file_rows = [
        ["harness.py",          "Orchestrates the full run pipeline"],
        ["schema.py",           "Pydantic models for test cases & results"],
        ["evaluators/",         "One file per evaluator strategy"],
        ["reporter/",           "HTML (Jinja2), JSON, CSV, SQLite history"],
        ["demo/test_cases/",    "38 ready-to-run YAML test cases"],
    ]
    table_box(slide, file_headers, file_rows,
              Inches(6.2), Inches(4.2), Inches(6.7), Inches(2.9))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    prs = new_prs()
    make_slide1(prs)
    make_slide2(prs)
    make_slide3(prs)
    make_slide4(prs)
    make_slide5(prs)
    make_slide6(prs)

    out = os.path.join(_DOCS_DIR, "auxilab_eval_harness.pptx")
    prs.save(out)
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()

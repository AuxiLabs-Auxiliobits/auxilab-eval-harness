#!/usr/bin/env python3
"""
Quick demo script showing all auxilab-eval-harness enhancements.
Run this to generate comprehensive reports with all features.
"""

from pathlib import Path
import subprocess
import sys

def print_section(title: str):
    """Print a pretty section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def run_ap_exception_demo():
    """Generate comprehensive AP Exception Agent report."""
    print_section("🧪 Running AP Exception Agent Evaluation (20 tests)")
    
    cmd = [
        "auxilab-eval", "run",
        "--tests", "demo/test_cases/ap_exception_tests.yaml",
        "--agent", "demo.ap_exception_agent:handle_ap_exception",
        "--html", "reports/ap_exception_report.html",
        "--json", "reports/ap_exception_report.json",
        "--csv", "reports/ap_exception_results.csv",
    ]
    
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n✅ AP Exception report generated:")
        print("   📄 HTML:  reports/ap_exception_report.html")
        print("   📊 JSON:  reports/ap_exception_report.json")
        print("   📋 CSV:   reports/ap_exception_results.csv")
    return result.returncode == 0

def run_payment_run_demo():
    """Generate comprehensive Payment Run Agent report."""
    print_section("💳 Running Payment Run Agent Evaluation (18 tests)")
    
    cmd = [
        "auxilab-eval", "run",
        "--tests", "demo/test_cases/payment_run_tests.yaml",
        "--agent", "demo.payment_run_agent:run_payment",
        "--html", "reports/payment_run_report.html",
        "--json", "reports/payment_run_report.json",
        "--csv", "reports/payment_run_results.csv",
    ]
    
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n✅ Payment Run report generated:")
        print("   📄 HTML:  reports/payment_run_report.html")
        print("   📊 JSON:  reports/payment_run_report.json")
        print("   📋 CSV:   reports/payment_run_results.csv")
    return result.returncode == 0

def show_history():
    """Display run history if available."""
    print_section("📜 Evaluation History")
    
    cmd = ["auxilab-eval", "history", "--limit", "10"]
    subprocess.run(cmd)

def main():
    print("\n" + "🚀 " * 20)
    print("  auxilab-eval-harness — Competition Demo")
    print("🚀 " * 20 + "\n")
    
    # Ensure reports directory exists
    Path("reports").mkdir(exist_ok=True)
    
    # Run demos
    ap_success = run_ap_exception_demo()
    payment_success = run_payment_run_demo()
    
    # Show history
    show_history()
    
    # Summary
    print_section("📊 Demo Summary")
    print("✨ Features Demonstrated:")
    print("   ✓ Rich CLI output with colored formatting")
    print("   ✓ 20 AP Exception test cases with edge cases")
    print("   ✓ 18 Payment Run test cases with security scenarios")
    print("   ✓ HTML reports with interactive features")
    print("   ✓ JSON exports for programmatic access")
    print("   ✓ CSV exports for spreadsheet analysis")
    print("   ✓ Performance metrics and timing data")
    print("   ✓ Failure classification and analysis")
    print("   ✓ Schema validation and semantic checks")
    print("   ✓ LLM-as-judge quality scoring")
    print("")
    
    if ap_success and payment_success:
        print("✅ All evaluations completed successfully!")
        print("\n📂 Generated Reports:")
        print("   reports/ap_exception_report.html")
        print("   reports/payment_run_report.html")
        print("\n💡 Next Steps:")
        print("   1. Open the HTML reports in your browser")
        print("   2. Explore the interactive filtering and charts")
        print("   3. Review the JSON files for detailed results")
        print("   4. Import CSV files into Excel for analysis")
        return 0
    else:
        print("❌ Some evaluations failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

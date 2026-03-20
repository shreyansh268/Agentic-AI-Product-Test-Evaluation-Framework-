# utils/validate_gates.py
"""
Quality gate validator.
Parses Behave JSON or Garak/Locust reports and asserts thresholds.
Exits with code 1 on any gate failure — triggers GH Actions pipeline failure.

Usage:
  python utils/validate_gates.py --report reports/rag_results.json --suite rag
  python utils/validate_gates.py --report reports/garak_report.json --suite security
  python utils/validate_gates.py --report reports/locust_single_stats.csv --suite performance
"""

import sys
import json
import argparse
import csv
from config.settings import GATES
from rich.console import Console
from rich.table import Table

console = Console()


def validate_rag(report_path: str) -> list[str]:
    """Parse Behave JSON for RAG suite; check RAGAS thresholds stored in scenario metadata."""
    failures = []
    # TODO: Load report, extract RAGAS scores from scenario extra data
    # Example structure expected in report:
    # { "ragas_faithfulness": 0.92, "ragas_completeness": 0.87, ... }
    try:
        with open(report_path) as f:
            data = json.load(f)
        scores = data.get("ragas_scores", {})
        if scores.get("faithfulness", 0) < GATES["ragas_faithfulness"]:
            failures.append(
                f"RAGAS Faithfulness {scores.get('faithfulness')} < gate {GATES['ragas_faithfulness']}"
            )
        if scores.get("context_recall", 0) < GATES["ragas_completeness"]:
            failures.append(
                f"RAGAS Context Recall {scores.get('context_recall')} < gate {GATES['ragas_completeness']}"
            )
        if scores.get("answer_relevancy", 0) < GATES["ragas_answer_relevance"]:
            failures.append(
                f"RAGAS Answer Relevancy {scores.get('answer_relevancy')} < gate {GATES['ragas_answer_relevance']}"
            )
    except (FileNotFoundError, json.JSONDecodeError):
        failures.append(f"Could not parse RAG report at {report_path}")
    return failures


def validate_agent(report_path: str) -> list[str]:
    """Parse Behave JSON for Agent suite; check trajectory and HITL assertions."""
    failures = []
    # TODO: Extract agent-specific metrics from report JSON
    # Currently checks for any failed scenarios in the agent suite
    try:
        with open(report_path) as f:
            data = json.load(f)
        for feature in data:
            for scenario in feature.get("elements", []):
                if scenario.get("status") == "failed":
                    failures.append(f"Agent scenario FAILED: {scenario.get('name')}")
    except (FileNotFoundError, json.JSONDecodeError):
        failures.append(f"Could not parse Agent report at {report_path}")
    return failures


def validate_security(report_path: str) -> list[str]:
    """Parse Garak JSON report; assert ASR below threshold."""
    failures = []
    try:
        with open(report_path) as f:
            data = json.load(f)
        asr = data.get("overall_asr", 1.0)
        if asr > GATES["garak_asr_max"]:
            failures.append(
                f"Garak ASR {asr:.4f} exceeds gate {GATES['garak_asr_max']} — "
                f"{data.get('failed_probes', [])} probes breached"
            )
    except (FileNotFoundError, json.JSONDecodeError):
        failures.append(f"Could not parse Security/Garak report at {report_path}")
    return failures


def validate_performance(report_path: str) -> list[str]:
    """Parse Locust CSV stats; assert P95 and error rate gates."""
    failures = []
    try:
        with open(report_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Name") == "Aggregated":
                    p95 = float(row.get("95%", 999999))
                    fail_pct = float(row.get("Failure Count", 1)) / max(float(row.get("Request Count", 1)), 1) * 100
                    if p95 > GATES["latency_p95_ms"]:
                        failures.append(
                            f"Locust P95 {p95:.0f}ms exceeds gate {GATES['latency_p95_ms']}ms"
                        )
                    if fail_pct > 1.0:
                        failures.append(
                            f"Locust error rate {fail_pct:.2f}% exceeds 1% gate"
                        )
    except (FileNotFoundError, KeyError) as e:
        failures.append(f"Could not parse Performance report at {report_path}: {e}")
    return failures


VALIDATORS = {
    "rag":         validate_rag,
    "agent":       validate_agent,
    "security":    validate_security,
    "performance": validate_performance,
}


def main():
    parser = argparse.ArgumentParser(description="Financial AI — Quality Gate Validator")
    parser.add_argument("--report", required=True, help="Path to the test report file")
    parser.add_argument("--suite",  required=True, choices=VALIDATORS.keys(), help="Test suite type")
    args = parser.parse_args()

    console.print(f"\n[bold cyan]Quality Gate Validation — Suite: {args.suite.upper()}[/bold cyan]")
    console.print(f"Report: {args.report}\n")

    validator = VALIDATORS[args.suite]
    failures = validator(args.report)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Status")
    table.add_column("Gate")

    if failures:
        for f in failures:
            table.add_row("[red]❌ FAIL[/red]", f)
        console.print(table)
        console.print(f"\n[bold red]🚨 {len(failures)} quality gate(s) FAILED — pipeline blocked[/bold red]\n")
        sys.exit(1)
    else:
        table.add_row("[green]✅ PASS[/green]", f"All {args.suite} quality gates met")
        console.print(table)
        console.print(f"\n[bold green]✅ All {args.suite} quality gates PASSED[/bold green]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

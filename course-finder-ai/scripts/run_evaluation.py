"""Run recommendation evaluation scenarios."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.runner import default_evaluation_cases, run_evaluation_case


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepEval-compatible recommendation evals.")
    parser.add_argument("--case", help="Optional case name to run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = default_evaluation_cases()
    if args.case:
        cases = [case for case in cases if case.name == args.case]
        if not cases:
            raise ValueError(f"Unknown evaluation case: {args.case}")

    all_passed = True
    for case in cases:
        report = run_evaluation_case(case)
        all_passed = all_passed and report.passed
        print(f"\nEvaluation Case: {report.case_name}")
        print(f"Query: {report.query}")
        print(f"Passed: {report.passed}")
        for metric in report.metric_scores:
            status = "PASS" if metric.success else "FAIL"
            print(f"- {metric.name}: {metric.score:.2f} [{status}]")
            print(f"  {metric.reason}")

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

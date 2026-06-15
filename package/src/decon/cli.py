"""CLI for standalone decontextualization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .eval import build_report, evaluate_cases, list_cases, load_default_suites, summarize_outcomes, write_report
from .service import build_decontextualizer, decontextualize_query
from .tasks import TaskMode


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    prog="decon",
    description="Decontextualize clinician queries into safe web-search prompts.",
  )
  parser.add_argument("query", nargs="?", help="Clinician free-text query")
  parser.add_argument(
    "--provider",
    default="anthropic",
    choices=["anthropic", "openai"],
    help="Model provider to use",
  )
  parser.add_argument(
    "--model",
    default="claude-haiku-4-5-20251001",
    help="Anthropic model to use",
  )
  parser.add_argument(
    "--patient-context",
    default="{}",
    help="JSON object used for local PHI validation",
  )
  parser.add_argument(
    "--mode",
    default=TaskMode.EXTERNAL_WEB_SEARCH.value,
    choices=[item.value for item in TaskMode],
    help="Task minimization mode",
  )
  parser.add_argument(
    "--eval",
    action="store_true",
    help="Run the bundled fixture suites against the live decontextualizer",
  )
  parser.add_argument(
    "--list-tests",
    action="store_true",
    help="Print the bundled fixture inventory and exit",
  )
  parser.add_argument(
    "--report",
    help="Write eval results to a JSON report file",
  )
  return parser


def main() -> int:
  parser = build_parser()
  args = parser.parse_args()
  cases = load_default_suites()

  if args.list_tests:
    print(json.dumps(list_cases(cases), indent=2))
    return 0

  if args.eval:
    runner = build_decontextualizer(provider=args.provider, model=args.model)
    outcomes = evaluate_cases(cases, decontextualizer=runner)
    summary = summarize_outcomes(outcomes)
    print(json.dumps(summary, indent=2))
    if args.report:
      report = build_report(outcomes, provider=args.provider, model=args.model)
      write_report(report, Path(args.report))
    return 0 if all(item.passed for item in outcomes) else 1

  try:
    patient_context = json.loads(args.patient_context)
  except json.JSONDecodeError as exc:
    parser.error(f"invalid --patient-context JSON: {exc}")

  if not args.query:
    parser.error("query is required unless --eval is used")

  query = decontextualize_query(
    args.query,
    provider=args.provider,
    model=args.model,
    patient_context=patient_context,
    mode=TaskMode(args.mode),
    validate=True,
  )

  print(query)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

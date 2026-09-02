"""CLI entrypoint for headless decon validation."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Sequence

from .validation_runner import (
  DEFAULT_DESTINATIONS,
  GENERATED_CLINICAL_SUITES,
  LEGACY_PHI_SUITES,
  CURRENT_SUITES,
  passes_thresholds,
  run_validation,
  write_report,
)
from .local_rules import OPENMED_ENGINE, SUPPORTED_ENGINES


SUITE_CHOICES = (
  "current",
  "release",
  "all",
  "legacy-phi",
  *CURRENT_SUITES.keys(),
  *GENERATED_CLINICAL_SUITES.keys(),
  *LEGACY_PHI_SUITES.keys(),
)


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    prog="decon-validate",
    description="Run local decon validation suites headlessly.",
  )
  parser.add_argument(
    "--suite",
    action="append",
    choices=SUITE_CHOICES,
    default=None,
    help="Suite to run. Repeat for multiple suites. Defaults to current.",
  )
  parser.add_argument(
    "--destinations",
    default=",".join(DEFAULT_DESTINATIONS),
    help="Comma-separated destinations. Defaults to chatgpt,gemini,web_search.",
  )
  parser.add_argument(
    "--reference-date",
    default="2026-06-15",
    help="Reference date for DOB-to-age conversion in YYYY-MM-DD format.",
  )
  parser.add_argument(
    "--engine",
    choices=tuple(sorted(SUPPORTED_ENGINES)),
    default=OPENMED_ENGINE,
    help="Decon engine to validate. Use rules+openmed to require the local OpenMed layer.",
  )
  parser.add_argument(
    "--min-clinical-usable",
    type=float,
    default=1.0,
    help="Minimum clinical usability rate for clinically labeled suites.",
  )
  parser.add_argument(
    "--allow-phi-leaks",
    action="store_true",
    help="Do not fail the process on detected PHI leaks. Useful for legacy exploration only.",
  )
  parser.add_argument(
    "--report",
    type=Path,
    help="Optional JSON report output path.",
  )
  parser.add_argument(
    "--json-only",
    action="store_true",
    help="Print the full JSON result instead of a compact text summary.",
  )
  return parser


def main(argv: Sequence[str] | None = None) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)
  suites = tuple(args.suite or ("current",))
  destinations = _parse_destinations(args.destinations)
  reference_date = _parse_reference_date(args.reference_date, parser)

  result = run_validation(
    suites=suites,
    destinations=destinations,
    reference_date=reference_date,
    engine=args.engine,
  )
  failures = passes_thresholds(
    result,
    fail_on_phi=not args.allow_phi_leaks,
    min_clinical_usable=args.min_clinical_usable,
  )
  result["passed"] = not failures
  result["failure_reasons"] = failures

  if args.report:
    write_report(result, args.report)

  if args.json_only:
    print(json.dumps(result, indent=2))
  else:
    print(_format_summary(result, report_path=args.report))

  return 0 if not failures else 1


def _parse_destinations(raw: str) -> tuple[str, ...]:
  destinations = tuple(item.strip() for item in raw.split(",") if item.strip())
  if not destinations:
    raise SystemExit("--destinations must include at least one destination")
  return destinations


def _parse_reference_date(raw: str, parser: argparse.ArgumentParser) -> date:
  try:
    return date.fromisoformat(raw)
  except ValueError:
    parser.error("--reference-date must use YYYY-MM-DD format")
  raise AssertionError("unreachable")


def _format_summary(result: dict[str, object], *, report_path: Path | None) -> str:
  summary = result["summary"]
  status = "PASS" if result["passed"] else "FAIL"
  lines = [
    f"Decon validation {status}",
    f"Suites: {', '.join(result['suites'])}",
    f"Destinations: {', '.join(result['destinations'])}",
    f"Engine: {result['engine']}",
    f"Source cases: {summary['source_cases']}",
    f"Outputs: {summary['outputs']}",
    f"PHI leaked outputs: {summary['phi_leaked_outputs']}",
    f"Unsafe copy-allowed leaks: {summary['unsafe_copy_allowed_outputs']}",
    f"Clinical labeled outputs: {summary['clinical_labeled_outputs']}",
    f"Clinically usable outputs: {summary['clinically_usable_outputs']}",
    f"Clinical usability rate: {summary['clinical_usable_rate']:.2%}",
    f"Handoff usability rate: {summary['handoff_usable_rate']:.2%}",
    f"Max avg runtime: {summary['avg_runtime_ms']} ms",
    f"Max p95 runtime: {summary['p95_runtime_ms']} ms",
  ]
  if result["failure_reasons"]:
    lines.append("Failures:")
    for reason in result["failure_reasons"]:
      lines.append(f"- {reason}")
  if report_path:
    lines.append(f"Report: {report_path}")
  return "\n".join(lines)


if __name__ == "__main__":
  raise SystemExit(main())

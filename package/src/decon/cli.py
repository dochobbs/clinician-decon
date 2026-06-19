"""CLI for local standalone decontextualization."""

from __future__ import annotations

import argparse
from datetime import date
import json
import sys
from typing import Sequence

from .destinations import DESTINATIONS
from .local_rules import OPENMED_ENGINE, SUPPORTED_ENGINES, decontextualize_text


DESTINATION_ALIASES = {
  "copy": "copy_only",
}


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    prog="decon",
    description="Decontextualize clinician text locally into a safer prompt.",
  )
  parser.add_argument(
    "text",
    nargs="?",
    help="Clinical text to decontextualize. If omitted, stdin is used.",
  )
  parser.add_argument(
    "--destination",
    default="copy",
    choices=tuple(sorted((*DESTINATIONS.keys(), *DESTINATION_ALIASES.keys()))),
    help="Prompt destination template. Defaults to copy-only output.",
  )
  parser.add_argument(
    "--engine",
    choices=tuple(sorted(SUPPORTED_ENGINES)),
    default=OPENMED_ENGINE,
    help="Local decon engine. Use rules+openmed to require the local model layer.",
  )
  parser.add_argument(
    "--reference-date",
    default=date.today().isoformat(),
    help="Reference date for DOB-to-age conversion in YYYY-MM-DD format.",
  )
  parser.add_argument(
    "--json",
    action="store_true",
    help="Print a JSON payload instead of only the destination prompt.",
  )
  return parser


def main(argv: Sequence[str] | None = None) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)
  text = args.text if args.text is not None else sys.stdin.read()
  text = text.strip()
  if not text:
    parser.error("text is required, either as an argument or on stdin")

  try:
    reference_date = date.fromisoformat(args.reference_date)
  except ValueError:
    parser.error("--reference-date must use YYYY-MM-DD format")

  destination_id = DESTINATION_ALIASES.get(args.destination, args.destination)
  result = decontextualize_text(
    text,
    destination=destination_id,
    reference_date=reference_date,
    engine=args.engine,
  )

  if args.json:
    print(json.dumps(_result_payload(result, requested_destination=args.destination), indent=2))
    if not result.copy_allowed:
      _print_blocked_warning(result)
      return 2
    return 0

  if not result.copy_allowed:
    _print_blocked_warning(result)
    return 2
  if result.risk_level != "low":
    print(
      f"Warning: decon risk is {result.risk_level}; review before copying.",
      file=sys.stderr,
    )
  print(result.destination_prompt)
  return 0


def _print_blocked_warning(result) -> None:
  reasons = "; ".join(result.risk_reasons) if result.risk_reasons else "high residual risk"
  print(f"Copy blocked: decon risk is {result.risk_level}. {reasons}", file=sys.stderr)


def _result_payload(result, *, requested_destination: str) -> dict[str, object]:
  return {
    "destination": requested_destination,
    "destination_id": result.destination,
    "engine": result.engine,
    "engine_requested": result.engine_requested,
    "engine_fallback_reason": result.engine_fallback_reason,
    "risk_level": result.risk_level,
    "risk_reasons": result.risk_reasons,
    "copy_allowed": result.copy_allowed,
    "open_url": result.open_url,
    "action_label": result.action_label,
    "removed_categories": result.removed_categories,
    "removed_spans": result.removed_spans,
    "safe_context": result.safe_context,
    "safe_query": result.safe_query,
    "destination_prompt": result.destination_prompt,
  }


if __name__ == "__main__":
  raise SystemExit(main())

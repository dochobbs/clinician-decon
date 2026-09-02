#!/usr/bin/env python3
"""Compare the deployed OpenMed arm with the experimental PPLX PII arm."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import time


PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_DIR.parent
sys.path.insert(0, str(PACKAGE_DIR / "src"))

from decon.local_rules import OPENMED_ENGINE, Span, decontextualize_text  # noqa: E402
from decon.openmed_ner import OpenMedSpanDetector  # noqa: E402
from decon.pplx_ner import PplxSpanDetector  # noqa: E402
from decon.usability_eval import evaluate_output, evaluation_to_dict  # noqa: E402
from decon.validation_runner import (  # noqa: E402
  CURRENT_SUITES,
  GENERATED_CLINICAL_SUITES,
  _load_usability_cases,
)


DEFAULT_SUITES = (
  "clinician-seed-gold",
  "validation-blindspot-redteam",
  "validation-blindspot-redteam-r2",
  "external-deid-adversarial-addon",
  "realworld-adversarial",
  "bare-name-shapes",
)
DEFAULT_DESTINATIONS = ("chatgpt", "gemini", "web_search")


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--suite",
    action="append",
    choices=("release", *tuple(CURRENT_SUITES), *tuple(GENERATED_CLINICAL_SUITES)),
  )
  # The generated release fixtures freeze age expectations against this date.
  # A later date can legitimately move a child into another age band and make
  # an otherwise correct output look like clinical-fact loss.
  parser.add_argument("--reference-date", type=date.fromisoformat, default=date(2026, 6, 15))
  parser.add_argument("--case-id", action="append")
  parser.add_argument("--destination", action="append")
  parser.add_argument("--device", default="cpu")
  parser.add_argument(
    "--arm",
    choices=("openmed", "pplx", "both"),
    default="both",
    help="Run one detector arm for focused iteration, or both for a head-to-head.",
  )
  parser.add_argument("--pplx-fix-mistral-regex", action="store_true")
  parser.add_argument(
    "--openmed-model-dir",
    type=Path,
    default=PACKAGE_DIR / "local-models" / "OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1",
  )
  parser.add_argument(
    "--pplx-model-dir",
    type=Path,
    default=PACKAGE_DIR / "local-models" / "perplexity-ai--pplx-pii-masking",
  )
  parser.add_argument(
    "--pplx-backbone-code-dir",
    type=Path,
    default=PACKAGE_DIR / "local-models" / "perplexity-ai--pplx-embed-v1-0.6b-code",
  )
  parser.add_argument("--report", type=Path)
  return parser.parse_args()


def mask_spans(text: str, spans: list[Span]) -> str:
  masked = text
  for span in sorted(spans, key=lambda item: (item.start, item.end), reverse=True):
    masked = masked[:span.start] + f"[{span.category.upper()}]" + masked[span.end:]
  return masked


def percentile(values: list[float], proportion: float) -> float:
  if not values:
    return 0.0
  index = min(len(values) - 1, int(len(values) * proportion))
  return sorted(values)[index]


def summarize(records: list[dict[str, object]], arm: str) -> dict[str, object]:
  detector_timings = [float(record["detector_ms"]) for record in records]
  model_only = [record["model_only"] for record in records]
  product = [
    evaluation
    for record in records
    for evaluation in record["products"].values()
  ]
  return {
    "arm": arm,
    "source_cases": len(records),
    "detector_errors": sum(bool(record.get("detector_error")) for record in records),
    "detector_only": {
      "phi_leaked_cases": sum(bool(item["leaked_phi"]) for item in model_only),
      "missing_critical_fact_cases": sum(
        bool(item["missing_critical_facts"]) for item in model_only
      ),
      "predicted_spans": sum(int(record["span_count"]) for record in records),
    },
    "product_pipeline": {
      "outputs": len(product),
      "phi_leaked_outputs": sum(bool(item["leaked_phi"]) for item in product),
      "missing_critical_fact_outputs": sum(
        bool(item["missing_critical_facts"]) for item in product
      ),
      "clinically_usable_outputs": sum(bool(item["clinically_usable"]) for item in product),
      "handoff_usable_outputs": sum(bool(item["handoff_usable"]) for item in product),
    },
    "detector_latency_ms": {
      "mean": round(statistics.fmean(detector_timings), 3),
      "p50": round(statistics.median(detector_timings), 3),
      "p95": round(percentile(detector_timings, 0.95), 3),
    },
  }


def evaluate_arm(
  *,
  arm: str,
  detector,
  cases,
  destinations: tuple[str, ...],
  reference_date: date,
) -> list[dict[str, object]]:
  records = []
  if cases:
    detector(cases[0].query)  # warm model load and first-tokenizer path outside timings
  for index, case in enumerate(cases, start=1):
    started = time.perf_counter()
    detector_error = None
    try:
      spans = detector(case.query)
    except Exception as exc:  # keep corpus evaluation running after length-specific failures
      spans = []
      detector_error = f"{type(exc).__name__}: {exc}"
    detector_ms = (time.perf_counter() - started) * 1000
    model_only_output = mask_spans(case.query, spans)
    model_only = evaluate_output(
      case,
      output=model_only_output,
      destination="detector_only",
      copy_allowed=True,
      risk_level="low",
    )
    products = {}
    product_result = None
    for destination in destinations:
      result = decontextualize_text(
        case.query,
        destination=destination,
        reference_date=reference_date,
        engine=OPENMED_ENGINE,
        span_detector=lambda _text, cached=tuple(spans): cached,
      )
      if product_result is None:
        product_result = result
      products[destination] = evaluation_to_dict(evaluate_output(
        case,
        output=result.destination_prompt,
        destination=destination,
        copy_allowed=result.copy_allowed,
        risk_level=result.risk_level,
      ))
    assert product_result is not None
    records.append({
      "arm": arm,
      "case_id": case.id,
      "suite": getattr(case, "suite", None),
      "category": case.category,
      "detector_ms": round(detector_ms, 3),
      "detector_error": detector_error,
      "span_count": len(spans),
      "sensitivity": getattr(detector, "last_sensitivity", None),
      "raw_predictions": getattr(detector, "last_predictions", None),
      "model_only": evaluation_to_dict(model_only),
      "products": products,
      "model_only_output": model_only_output,
      "product_safe_context": product_result.safe_context,
      "removed_spans": product_result.removed_spans,
    })
    if index == 1 or index == len(cases) or index % 25 == 0:
      print(f"{arm}: {index}/{len(cases)} {case.id}", flush=True)
  return records


def main() -> int:
  args = parse_args()
  requested_suites = tuple(args.suite or DEFAULT_SUITES)
  suites = []
  for suite in requested_suites:
    expanded = (
      (*tuple(CURRENT_SUITES), *tuple(GENERATED_CLINICAL_SUITES))
      if suite == "release"
      else (suite,)
    )
    for item in expanded:
      if item not in suites:
        suites.append(item)
  suites = tuple(suites)
  destinations = tuple(args.destination or DEFAULT_DESTINATIONS)
  cases = []
  case_suites: dict[str, str] = {}
  for suite in suites:
    loaded = (
      GENERATED_CLINICAL_SUITES[suite]()
      if suite in GENERATED_CLINICAL_SUITES
      else _load_usability_cases(CURRENT_SUITES[suite])
    )
    cases.extend(loaded)
    case_suites.update({case.id: suite for case in loaded})
  if args.case_id:
    selected = set(args.case_id)
    cases = [case for case in cases if case.id in selected]
    missing = selected - {case.id for case in cases}
    if missing:
      raise SystemExit(f"unknown case id(s): {', '.join(sorted(missing))}")

  openmed_records = []
  pplx_records = []
  if args.arm in ("openmed", "both"):
    openmed_records = evaluate_arm(
      arm="rules+openmed",
      detector=OpenMedSpanDetector(model_dir=args.openmed_model_dir),
      cases=cases,
      destinations=destinations,
      reference_date=args.reference_date,
    )
  if args.arm in ("pplx", "both"):
    pplx_records = evaluate_arm(
      arm="rules+pplx",
      detector=PplxSpanDetector(
        model_dir=args.pplx_model_dir,
        backbone_code_dir=args.pplx_backbone_code_dir,
        device=args.device,
        fix_mistral_regex=args.pplx_fix_mistral_regex,
      ),
      cases=cases,
      destinations=destinations,
      reference_date=args.reference_date,
    )
  all_records = [*openmed_records, *pplx_records]
  for record in all_records:
    record["suite"] = case_suites[str(record["case_id"])]

  disagreements = []
  if openmed_records and pplx_records:
    openmed_by_id = {str(record["case_id"]): record for record in openmed_records}
    for record in pplx_records:
      prior = openmed_by_id[str(record["case_id"])]
      if record["product_safe_context"] != prior["product_safe_context"]:
        disagreements.append({
          "case_id": record["case_id"],
          "suite": record["suite"],
          "category": record["category"],
          "openmed_safe_context": prior["product_safe_context"],
          "pplx_safe_context": record["product_safe_context"],
          "openmed_products": prior["products"],
          "pplx_products": record["products"],
        })

  report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "reference_date": args.reference_date.isoformat(),
    "destinations": list(destinations),
    "pplx_fix_mistral_regex": args.pplx_fix_mistral_regex,
    "arm": args.arm,
    "suites": list(suites),
    "models": {
      "openmed": str(args.openmed_model_dir),
      "pplx": str(args.pplx_model_dir),
      "pplx_backbone_code": str(args.pplx_backbone_code_dir),
    },
    "summaries": [
      *([summarize(openmed_records, "rules+openmed")] if openmed_records else []),
      *([summarize(pplx_records, "rules+pplx")] if pplx_records else []),
    ],
    "product_output_disagreements": len(disagreements),
    "disagreements": disagreements,
    "records": all_records,
  }
  console_report = {
    key: value
    for key, value in report.items()
    if key not in ("records", "disagreements")
  }
  print(json.dumps(console_report, indent=2))
  if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {args.report}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

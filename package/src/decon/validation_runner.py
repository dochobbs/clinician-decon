"""Headless validation runner for local decontextualization gates."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Iterable

from .local_rules import decontextualize_text
from .usability_eval import (
  CriticalFact,
  UsabilityCase,
  evaluation_to_dict,
  evaluate_output,
)


PACKAGE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = PACKAGE_DIR.parent
DATA_DIR = PACKAGE_DIR / "data"

CURRENT_SUITES = {
  "usability": DATA_DIR / "decon_usability_500_2026-06-15.json",
  "adversarial": DATA_DIR / "decon_adversarial_500_2026-06-15.json",
  "phi-field-prose": DATA_DIR / "decon_phi_field_prose_25_2026-06-15.json",
  "validation-blindspot-redteam": DATA_DIR / "decon_validation_blindspot_redteam_17_2026-06-15.json",
  "validation-blindspot-redteam-r2": DATA_DIR / "decon_validation_blindspot_redteam_r2_25_2026-06-15.json",
  "persona-regression": DATA_DIR / "decon_persona_regression_2000_2026-06-15.json",
}

LEGACY_PHI_SUITES = {
  "legacy-synth-500": REPO_ROOT / "from-cds-eval" / "data" / "decon_synth_500.json",
  "legacy-synth-500-b": REPO_ROOT / "from-cds-eval" / "data" / "decon_synth_500_b.json",
  "legacy-amboss-stress": REPO_ROOT / "from-cds-eval" / "data" / "decon_amboss_stress.json",
  "legacy-combined-1132": REPO_ROOT / "from-cds-eval" / "data" / "decon_combined_1132.json",
}

DEFAULT_DESTINATIONS = ("chatgpt", "gemini", "web_search")


def run_validation(
  *,
  suites: Iterable[str],
  destinations: Iterable[str] = DEFAULT_DESTINATIONS,
  reference_date: date,
) -> dict[str, object]:
  """Run one or more validation suites and return a CI-friendly summary."""
  suite_names = _expand_suite_names(tuple(suites))
  destination_names = tuple(destinations)
  suite_results = []

  for suite_name in suite_names:
    if suite_name in CURRENT_SUITES:
      suite_results.append(_run_clinical_suite(
        suite_name=suite_name,
        path=CURRENT_SUITES[suite_name],
        destinations=destination_names,
        reference_date=reference_date,
      ))
    elif suite_name in LEGACY_PHI_SUITES:
      suite_results.append(_run_legacy_phi_suite(
        suite_name=suite_name,
        path=LEGACY_PHI_SUITES[suite_name],
        destinations=destination_names,
        reference_date=reference_date,
      ))
    else:
      raise ValueError(f"unknown validation suite: {suite_name}")

  return {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "reference_date": reference_date.isoformat(),
    "destinations": list(destination_names),
    "suites": list(suite_names),
    "summary": _aggregate_summaries(item["summary"] for item in suite_results),
    "suite_results": suite_results,
  }


def passes_thresholds(
  result: dict[str, object],
  *,
  fail_on_phi: bool,
  min_clinical_usable: float,
) -> list[str]:
  """Return human-readable failure reasons for a validation result."""
  summary = result["summary"]
  failures = []
  phi_leaked_outputs = int(summary["phi_leaked_outputs"])
  unsafe_copy_allowed_outputs = int(summary["unsafe_copy_allowed_outputs"])
  clinical_labeled_outputs = int(summary["clinical_labeled_outputs"])
  clinical_usable_rate = float(summary["clinical_usable_rate"])

  if fail_on_phi and phi_leaked_outputs:
    failures.append(f"PHI leaked in {phi_leaked_outputs} output(s).")
  if fail_on_phi and unsafe_copy_allowed_outputs:
    failures.append(
      f"Unsafe copy was allowed for {unsafe_copy_allowed_outputs} PHI-leaking output(s)."
    )
  if clinical_labeled_outputs and clinical_usable_rate < min_clinical_usable:
    failures.append(
      "Clinical usability rate "
      f"{clinical_usable_rate:.2%} is below required {min_clinical_usable:.2%}."
    )
  return failures


def write_report(result: dict[str, object], output_path: Path) -> None:
  """Write a validation report JSON file."""
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def _expand_suite_names(suites: tuple[str, ...]) -> tuple[str, ...]:
  expanded = []
  for suite in suites:
    if suite == "current":
      expanded.extend(("usability", "adversarial"))
    elif suite == "legacy-phi":
      expanded.extend(("legacy-synth-500", "legacy-synth-500-b", "legacy-amboss-stress"))
    elif suite == "all":
      expanded.extend((
        "usability",
        "adversarial",
        "legacy-synth-500",
        "legacy-synth-500-b",
        "legacy-amboss-stress",
      ))
    else:
      expanded.append(suite)

  deduped = []
  for suite in expanded:
    if suite not in deduped:
      deduped.append(suite)
  return tuple(deduped)


def _run_clinical_suite(
  *,
  suite_name: str,
  path: Path,
  destinations: tuple[str, ...],
  reference_date: date,
) -> dict[str, object]:
  cases = _load_usability_cases(path)
  records = []
  timings = []

  for case in cases:
    for destination in destinations:
      start = time.perf_counter()
      result = decontextualize_text(
        case.query,
        destination=destination,
        reference_date=reference_date,
      )
      timings.append(time.perf_counter() - start)
      evaluation = evaluate_output(
        case,
        output=result.destination_prompt,
        destination=destination,
        copy_allowed=result.copy_allowed,
        risk_level=result.risk_level,
      )
      records.append({
        "case_id": case.id,
        "category": case.category,
        "destination": destination,
        "risk_level": result.risk_level,
        "copy_allowed": result.copy_allowed,
        "evaluation": evaluation_to_dict(evaluation),
      })

  summary = _summarize_records(
    suite_name=suite_name,
    source_cases=len(cases),
    records=records,
    timings=timings,
    clinical_labeled=True,
  )
  return {
    "suite": suite_name,
    "path": str(path.relative_to(REPO_ROOT)),
    "kind": "clinical-usability",
    "summary": summary,
    "failures": _representative_failures(records),
  }


def _run_legacy_phi_suite(
  *,
  suite_name: str,
  path: Path,
  destinations: tuple[str, ...],
  reference_date: date,
) -> dict[str, object]:
  cases = json.loads(path.read_text(encoding="utf-8"))
  records = []
  timings = []

  for case in cases:
    phi_terms = tuple(case.get("phi") or ())
    for destination in destinations:
      start = time.perf_counter()
      result = decontextualize_text(
        case["query"],
        destination=destination,
        reference_date=reference_date,
      )
      timings.append(time.perf_counter() - start)
      output = _copied_output(result, destination)
      leaked_phi = [term for term in phi_terms if _contains_term(output, term)]
      records.append({
        "case_id": case.get("id"),
        "category": case.get("category"),
        "destination": destination,
        "risk_level": result.risk_level,
        "copy_allowed": result.copy_allowed,
        "evaluation": {
          "leaked_phi": leaked_phi,
          "missing_critical_facts": [],
          "flags": ["phi_leak"] if leaked_phi else [],
          "clinically_usable": None,
          "handoff_usable": None,
        },
      })

  summary = _summarize_records(
    suite_name=suite_name,
    source_cases=len(cases),
    records=records,
    timings=timings,
    clinical_labeled=False,
  )
  return {
    "suite": suite_name,
    "path": str(path.relative_to(REPO_ROOT)),
    "kind": "phi-only",
    "summary": summary,
    "failures": _representative_failures(records),
  }


def _load_usability_cases(path: Path) -> list[UsabilityCase]:
  payload = json.loads(path.read_text(encoding="utf-8"))
  cases = []
  for item in payload:
    facts = tuple(
      CriticalFact(
        label=fact["label"],
        acceptable_terms=tuple(fact["acceptable_terms"]),
      )
      for fact in item["critical_facts"]
    )
    cases.append(UsabilityCase(
      id=item["id"],
      category=item["category"],
      query=item["query"],
      phi=tuple(item["phi"]),
      critical_facts=facts,
      forbidden_terms=tuple(item.get("forbidden_terms") or ()),
    ))
  return cases


def _summarize_records(
  *,
  suite_name: str,
  source_cases: int,
  records: list[dict[str, object]],
  timings: list[float],
  clinical_labeled: bool,
) -> dict[str, object]:
  outputs = len(records)
  safe_outputs = 0
  clinically_usable_outputs = 0
  handoff_usable_outputs = 0
  phi_leaked_outputs = 0
  unsafe_copy_allowed_outputs = 0
  missing_critical_fact_outputs = 0
  leaked_terms = 0
  by_destination: dict[str, dict[str, int]] = {}
  by_category: dict[str, dict[str, int]] = {}

  for record in records:
    evaluation = record["evaluation"]
    leaked_phi = evaluation["leaked_phi"]
    missing_facts = evaluation["missing_critical_facts"]
    leaked = bool(leaked_phi)
    missing = bool(missing_facts)
    clinically_usable = bool(evaluation["clinically_usable"]) if clinical_labeled else False
    handoff_usable = bool(evaluation["handoff_usable"]) if clinical_labeled else False
    unsafe_copy_allowed = leaked and bool(record["copy_allowed"])

    safe_outputs += int(not leaked)
    phi_leaked_outputs += int(leaked)
    unsafe_copy_allowed_outputs += int(unsafe_copy_allowed)
    missing_critical_fact_outputs += int(missing)
    leaked_terms += len(leaked_phi)
    clinically_usable_outputs += int(clinically_usable)
    handoff_usable_outputs += int(handoff_usable)
    _increment_bucket(by_destination, str(record["destination"]), leaked, missing, unsafe_copy_allowed)
    _increment_bucket(by_category, str(record["category"]), leaked, missing, unsafe_copy_allowed)

  clinical_labeled_outputs = outputs if clinical_labeled else 0
  avg_runtime_ms = round(sum(timings) / len(timings) * 1000, 3) if timings else 0
  p95_runtime_ms = round(sorted(timings)[int(len(timings) * 0.95)] * 1000, 3) if timings else 0
  return {
    "suite": suite_name,
    "source_cases": source_cases,
    "outputs": outputs,
    "clinical_labeled_outputs": clinical_labeled_outputs,
    "safe_outputs": safe_outputs,
    "phi_leaked_outputs": phi_leaked_outputs,
    "unsafe_copy_allowed_outputs": unsafe_copy_allowed_outputs,
    "missing_critical_fact_outputs": missing_critical_fact_outputs,
    "clinically_usable_outputs": clinically_usable_outputs,
    "handoff_usable_outputs": handoff_usable_outputs,
    "leaked_terms": leaked_terms,
    "safe_rate": _rate(safe_outputs, outputs),
    "clinical_usable_rate": _rate(clinically_usable_outputs, clinical_labeled_outputs),
    "handoff_usable_rate": _rate(handoff_usable_outputs, clinical_labeled_outputs),
    "avg_runtime_ms": avg_runtime_ms,
    "p95_runtime_ms": p95_runtime_ms,
    "by_destination": by_destination,
    "by_category": by_category,
  }


def _aggregate_summaries(summaries: Iterable[dict[str, object]]) -> dict[str, object]:
  items = list(summaries)
  source_cases = sum(int(item["source_cases"]) for item in items)
  outputs = sum(int(item["outputs"]) for item in items)
  clinical_labeled_outputs = sum(int(item["clinical_labeled_outputs"]) for item in items)
  safe_outputs = sum(int(item["safe_outputs"]) for item in items)
  phi_leaked_outputs = sum(int(item["phi_leaked_outputs"]) for item in items)
  unsafe_copy_allowed_outputs = sum(int(item["unsafe_copy_allowed_outputs"]) for item in items)
  missing_critical_fact_outputs = sum(int(item["missing_critical_fact_outputs"]) for item in items)
  clinically_usable_outputs = sum(int(item["clinically_usable_outputs"]) for item in items)
  handoff_usable_outputs = sum(int(item["handoff_usable_outputs"]) for item in items)
  leaked_terms = sum(int(item["leaked_terms"]) for item in items)
  avg_runtime_values = [
    float(item["avg_runtime_ms"])
    for item in items
    if int(item["outputs"]) > 0
  ]
  p95_runtime_values = [
    float(item["p95_runtime_ms"])
    for item in items
    if int(item["outputs"]) > 0
  ]

  return {
    "source_cases": source_cases,
    "outputs": outputs,
    "clinical_labeled_outputs": clinical_labeled_outputs,
    "safe_outputs": safe_outputs,
    "phi_leaked_outputs": phi_leaked_outputs,
    "unsafe_copy_allowed_outputs": unsafe_copy_allowed_outputs,
    "missing_critical_fact_outputs": missing_critical_fact_outputs,
    "clinically_usable_outputs": clinically_usable_outputs,
    "handoff_usable_outputs": handoff_usable_outputs,
    "leaked_terms": leaked_terms,
    "safe_rate": _rate(safe_outputs, outputs),
    "clinical_usable_rate": _rate(clinically_usable_outputs, clinical_labeled_outputs),
    "handoff_usable_rate": _rate(handoff_usable_outputs, clinical_labeled_outputs),
    "avg_runtime_ms": round(max(avg_runtime_values), 3) if avg_runtime_values else 0,
    "p95_runtime_ms": round(max(p95_runtime_values), 3) if p95_runtime_values else 0,
  }


def _increment_bucket(
  bucket: dict[str, dict[str, int]],
  key: str,
  leaked: bool,
  missing: bool,
  unsafe_copy_allowed: bool,
) -> None:
  stats = bucket.setdefault(
    key,
    {
      "outputs": 0,
      "safe": 0,
      "phi_leaked": 0,
      "missing_critical_fact": 0,
      "unsafe_copy_allowed": 0,
    },
  )
  stats["outputs"] += 1
  stats["safe"] += int(not leaked)
  stats["phi_leaked"] += int(leaked)
  stats["missing_critical_fact"] += int(missing)
  stats["unsafe_copy_allowed"] += int(unsafe_copy_allowed)


def _representative_failures(records: list[dict[str, object]], limit: int = 20) -> list[dict[str, object]]:
  failures = []
  for record in records:
    evaluation = record["evaluation"]
    if evaluation["leaked_phi"] or evaluation["missing_critical_facts"]:
      failures.append({
        "case_id": record["case_id"],
        "category": record["category"],
        "destination": record["destination"],
        "risk_level": record["risk_level"],
        "copy_allowed": record["copy_allowed"],
        "leaked_phi": evaluation["leaked_phi"],
        "missing_critical_facts": evaluation["missing_critical_facts"],
      })
    if len(failures) == limit:
      break
  return failures


def _contains_term(text: str, term: str) -> bool:
  if not term:
    return False
  pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)
  return bool(pattern.search(text))


def _copied_output(result: object, destination: str) -> str:
  if destination == "web_search":
    return result.safe_query
  return result.destination_prompt


def _rate(numerator: int, denominator: int) -> float:
  if denominator == 0:
    return 0.0
  return round(numerator / denominator, 6)

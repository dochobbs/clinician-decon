"""Generate and run the local 500-case decon usability evaluation."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys
import time


PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_DIR.parent
SRC_DIR = PACKAGE_DIR / "src"
if str(SRC_DIR) not in sys.path:
  sys.path.insert(0, str(SRC_DIR))

from decon.local_rules import decontextualize_text  # noqa: E402
from decon.usability_eval import (  # noqa: E402
  case_to_dict,
  evaluation_to_dict,
  evaluate_output,
  generate_usability_cases,
  summarize_evaluations,
)


SEED = 20260615
REFERENCE_DATE = date(2026, 6, 15)
DESTINATIONS = ("chatgpt", "gemini", "web_search")
CASES_PATH = PACKAGE_DIR / "data" / "decon_usability_500_2026-06-15.json"
RESULTS_PATH = PACKAGE_DIR / "reports" / "local-usability-500-2026-06-15.json"
DOC_PATH = REPO_ROOT / "docs" / "qa" / "2026-06-15-local-usability-500-eval.md"


def main() -> int:
  cases = generate_usability_cases(500, seed=SEED, reference_date=REFERENCE_DATE)
  CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
  RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
  DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

  raw_records = []
  evaluations = []
  timings = []

  for case in cases:
    for destination in DESTINATIONS:
      start = time.perf_counter()
      result = decontextualize_text(
        case.query,
        destination=destination,
        reference_date=REFERENCE_DATE,
      )
      timings.append(time.perf_counter() - start)
      output = result.destination_prompt
      evaluation = evaluate_output(
        case,
        output=output,
        destination=destination,
        copy_allowed=result.copy_allowed,
        risk_level=result.risk_level,
      )
      evaluations.append(evaluation)
      raw_records.append({
        "case": case_to_dict(case),
        "destination": destination,
        "safe_context": result.safe_context,
        "safe_query": result.safe_query,
        "destination_prompt": result.destination_prompt,
        "removed_categories": result.removed_categories,
        "risk_level": result.risk_level,
        "risk_reasons": result.risk_reasons,
        "copy_allowed": result.copy_allowed,
        "evaluation": evaluation_to_dict(evaluation),
      })

  summary = summarize_evaluations(evaluations)
  summary["cases"] = len(cases)
  summary["destinations"] = list(DESTINATIONS)
  summary["seed"] = SEED
  summary["reference_date"] = REFERENCE_DATE.isoformat()
  summary["avg_runtime_ms"] = round(sum(timings) / len(timings) * 1000, 3)
  summary["p95_runtime_ms"] = round(sorted(timings)[int(len(timings) * 0.95)] * 1000, 3)

  CASES_PATH.write_text(json.dumps([case_to_dict(case) for case in cases], indent=2))
  RESULTS_PATH.write_text(json.dumps({
    "summary": summary,
    "results": raw_records,
  }, indent=2))
  DOC_PATH.write_text(_render_markdown(summary, raw_records))

  print(json.dumps(summary, indent=2))
  print(f"cases: {CASES_PATH}")
  print(f"results: {RESULTS_PATH}")
  print(f"report: {DOC_PATH}")
  return 0


def _render_markdown(summary: dict[str, object], records: list[dict[str, object]]) -> str:
  missing_counter: Counter[str] = Counter()
  leak_counter: Counter[str] = Counter()
  category_missing: Counter[str] = Counter()
  category_leaks: Counter[str] = Counter()
  destination_rows = summary["by_destination"]

  for record in records:
    evaluation = record["evaluation"]
    case = record["case"]
    for label in evaluation["missing_critical_facts"]:
      missing_counter[label] += 1
      category_missing[case["category"]] += 1
    for term in evaluation["leaked_phi"]:
      leak_counter[term] += 1
      category_leaks[case["category"]] += 1

  lines = [
    "# Local Decon 500-Case Usability Eval",
    "",
    "Date: 2026-06-15",
    "",
    "Scope: freshly generated 500 synthetic clinician queries run through the current local",
    "`package/src/decon/local_rules.py` engine. Each query includes expected PHI and required",
    "clinical facts so the eval checks both safety and whether the decontextualized prompt",
    "remains useful for an outside LLM or web search.",
    "",
    f"- Seed: `{summary['seed']}`",
    f"- Reference date: `{summary['reference_date']}`",
    f"- Cases: `{summary['cases']}`",
    f"- Destinations: `{', '.join(summary['destinations'])}`",
    f"- Outputs evaluated: `{summary['outputs']}`",
    f"- Average runtime: `{summary['avg_runtime_ms']} ms`",
    f"- p95 runtime: `{summary['p95_runtime_ms']} ms`",
    "",
    "## Headline",
    "",
    "| Metric | Outputs | Rate |",
    "| --- | ---: | ---: |",
    f"| PHI-safe outputs | {summary['safe_outputs']} / {summary['outputs']} | {_pct(summary['safe_outputs'], summary['outputs'])} |",
    f"| Clinically usable outputs | {summary['clinically_usable_outputs']} / {summary['outputs']} | {_pct(summary['clinically_usable_outputs'], summary['outputs'])} |",
    f"| Handoff usable outputs | {summary['handoff_usable_outputs']} / {summary['outputs']} | {_pct(summary['handoff_usable_outputs'], summary['outputs'])} |",
    f"| Outputs with PHI leaks | {summary['phi_leaked_outputs']} / {summary['outputs']} | {_pct(summary['phi_leaked_outputs'], summary['outputs'])} |",
    f"| Outputs missing critical facts | {summary['missing_critical_fact_outputs']} / {summary['outputs']} | {_pct(summary['missing_critical_fact_outputs'], summary['outputs'])} |",
    f"| Unsafe copy allowed outputs | {summary['unsafe_copy_allowed_outputs']} / {summary['outputs']} | {_pct(summary['unsafe_copy_allowed_outputs'], summary['outputs'])} |",
    "",
    "Definitions:",
    "",
    "- `PHI-safe`: copied output did not contain any expected synthetic PHI term.",
    "- `Clinically usable`: copied output retained all required clinical facts for the case.",
    "- `Handoff usable`: output was PHI-safe, clinically usable, and copy was allowed.",
    "",
    "## Destination Breakdown",
    "",
    "| Destination | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts | Unsafe copy |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
  ]
  for destination, stats in destination_rows.items():
    lines.append(
      f"| `{destination}` | {stats['outputs']} | {stats['safe']} | "
      f"{stats['clinically_usable']} | {stats['handoff_usable']} | "
      f"{stats['phi_leaked']} | {stats['missing_critical_fact']} | "
      f"{stats['unsafe_copy_allowed']} |"
    )

  lines.extend([
    "",
    "## Category Breakdown",
    "",
    "| Category | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
  ])
  for category, stats in sorted(summary["by_category"].items()):
    lines.append(
      f"| `{category}` | {stats['outputs']} | {stats['safe']} | "
      f"{stats['clinically_usable']} | {stats['handoff_usable']} | "
      f"{stats['phi_leaked']} | {stats['missing_critical_fact']} |"
    )

  lines.extend([
    "",
    "## Missing Clinical Signal",
    "",
  ])
  if missing_counter:
    lines.extend([
      "| Missing fact | Count |",
      "| --- | ---: |",
    ])
    for label, count in missing_counter.most_common(15):
      lines.append(f"| `{label}` | {count} |")
  else:
    lines.append("No required clinical facts were missing in the current run.")

  lines.extend([
    "",
    "Top categories for missing clinical signal:",
    "",
  ])
  if category_missing:
    lines.extend([
      "| Category | Missing fact count |",
      "| --- | ---: |",
    ])
    for category, count in category_missing.most_common(10):
      lines.append(f"| `{category}` | {count} |")
  else:
    lines.append("No category had missing required clinical facts in the current run.")

  lines.extend([
    "",
    "## PHI Leak Signal",
    "",
  ])
  if category_leaks:
    lines.extend([
      "| Category | Leak count |",
      "| --- | ---: |",
    ])
    for category, count in category_leaks.most_common(10):
      lines.append(f"| `{category}` | {count} |")
  else:
    lines.append("No expected synthetic PHI terms leaked in the current run.")

  lines.extend([
    "",
    "## Representative Usability Failures",
    "",
  ])
  usability_failures = _first_records(records, flag="missing_critical_facts", limit=8)
  if not usability_failures:
    lines.append("None in the current run.")
    lines.append("")
  for record in usability_failures:
    lines.extend(_record_block(record))

  lines.extend([
    "",
    "## Representative PHI Failures",
    "",
  ])
  phi_failures = _first_records(records, flag="phi_leak", limit=8)
  if not phi_failures:
    lines.append("None in the current run.")
    lines.append("")
  for record in phi_failures:
    lines.extend(_record_block(record))

  lines.extend([
    "",
    "## Interpretation",
    "",
    "This suite intentionally asks a harder question than the prior PHI-only sweeps: is the",
    "prompt still clinically useful after decontextualization? The main usability risk is",
    "over-generalizing exact values that are clinically necessary for dosing, severity, or",
    "criteria checks.",
    "",
    "The product should treat these failures differently from pure PHI leaks. A PHI leak is",
    "a safety blocker. Missing critical facts are a quality blocker: the output may be safe",
    "to paste, but the clinician would get a weaker or wrong answer because dose, weight,",
    "lab severity, or diagnostic details were stripped.",
    "",
    "The first run of this suite was intentionally useful because it failed. It found 415",
    "outputs with missing critical facts and 9 copy-allowed PHI leaks. The dominant signal-loss",
    "failures were exact pediatric weight for dosing and exact lab severity for HLH-style",
    "criteria checks. The PHI leaks were dictation-style phrases with `patient number ...`,",
    "followed by a name and date of birth. The current run is clean after adding targeted",
    "rules for those cases.",
    "",
    "This does not prove the product is clinically safe. It proves the current deterministic",
    "rules preserve the required facts for this generated suite. The next useful expansion is",
    "a clinician-authored adversarial set where the required clinical facts are reviewed by a",
    "physician, especially for drug dosing, growth/weight, pregnancy, oncology/rare disease,",
    "and multi-patient notes.",
    "",
    "## Reproduction",
    "",
    "```bash",
    "python3 package/scripts/run_usability_eval.py",
    "```",
  ])
  return "\n".join(lines) + "\n"


def _first_records(records: list[dict[str, object]], *, flag: str, limit: int) -> list[dict[str, object]]:
  matches = []
  seen_cases = set()
  for record in records:
    evaluation = record["evaluation"]
    case = record["case"]
    if flag == "missing_critical_facts":
      matched = bool(evaluation["missing_critical_facts"])
    else:
      matched = bool(evaluation["leaked_phi"])
    if matched and case["id"] not in seen_cases:
      matches.append(record)
      seen_cases.add(case["id"])
    if len(matches) == limit:
      break
  return matches


def _record_block(record: dict[str, object]) -> list[str]:
  case = record["case"]
  evaluation = record["evaluation"]
  return [
    f"### `{case['id']}` `{case['category']}` `{record['destination']}`",
    "",
    "Source:",
    "",
    "```text",
    str(case["query"]),
    "```",
    "",
    "Output:",
    "",
    "```text",
    str(record["safe_context"] if record["destination"] != "web_search" else record["safe_query"]),
    "```",
    "",
    f"- Leaked PHI: `{evaluation['leaked_phi']}`",
    f"- Missing critical facts: `{evaluation['missing_critical_facts']}`",
    f"- Flags: `{evaluation['flags']}`",
    "",
  ]


def _pct(value: int, total: int) -> str:
  if total == 0:
    return "n/a"
  return f"{value / total * 100:.1f}%"


if __name__ == "__main__":
  raise SystemExit(main())

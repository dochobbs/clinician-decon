"""Generate and run the local 500-case adversarial decon evaluation."""

from __future__ import annotations

from collections import Counter
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
  generate_adversarial_cases,
  summarize_evaluations,
)


SEED = 20260615
REFERENCE_DATE = date(2026, 6, 15)
DESTINATIONS = ("chatgpt", "gemini", "web_search")
CASES_PATH = PACKAGE_DIR / "data" / "decon_adversarial_500_2026-06-15.json"
RESULTS_PATH = PACKAGE_DIR / "reports" / "local-adversarial-500-2026-06-15.json"
DOC_PATH = REPO_ROOT / "docs" / "qa" / "2026-06-15-local-adversarial-500-eval.md"


def main() -> int:
  cases = generate_adversarial_cases(500, seed=SEED, reference_date=REFERENCE_DATE)
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
  summary["suite"] = "adversarial"
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
    "# Local Decon 500-Case Adversarial Eval",
    "",
    "Date: 2026-06-15",
    "",
    "Scope: deterministic adversarial synthetic queries run through the current local",
    "`package/src/decon/local_rules.py` engine. This suite targets common product failure",
    "modes that are easy to miss in broad randomized PHI sweeps: prompt-injection text,",
    "buried patient identity, eponym collisions, repeated sibling names, OCR-spaced",
    "identifiers, URL-embedded PHI, Spanish family phrasing, small-town uniqueness,",
    "copy-pasted note sections, and contact/date mashups.",
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
    "## Destination Breakdown",
    "",
    "| Destination | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts | Unsafe copy |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
  ]
  for destination, stats in summary["by_destination"].items():
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

  lines.extend(["", "## PHI Leak Signal", ""])
  if category_leaks:
    lines.extend(["| Category | Leak count |", "| --- | ---: |"])
    for category, count in category_leaks.most_common(10):
      lines.append(f"| `{category}` | {count} |")
  else:
    lines.append("No expected synthetic PHI terms leaked in the current run.")

  lines.extend(["", "## Missing Clinical Signal", ""])
  if missing_counter:
    lines.extend(["| Missing fact | Count |", "| --- | ---: |"])
    for label, count in missing_counter.most_common(15):
      lines.append(f"| `{label}` | {count} |")
  else:
    lines.append("No required clinical facts were missing in the current run.")

  lines.extend(["", "## Representative PHI Failures", ""])
  phi_failures = _first_records(records, leak=True, limit=10)
  if not phi_failures:
    lines.append("None in the current run.")
    lines.append("")
  for record in phi_failures:
    lines.extend(_record_block(record))

  lines.extend(["", "## Representative Usability Failures", ""])
  usability_failures = _first_records(records, leak=False, limit=10)
  if not usability_failures:
    lines.append("None in the current run.")
    lines.append("")
  for record in usability_failures:
    lines.extend(_record_block(record))

  lines.extend([
    "",
    "## Reproduction",
    "",
    "```bash",
    "python3 package/scripts/run_adversarial_eval.py",
    "```",
  ])
  return "\n".join(lines) + "\n"


def _first_records(
  records: list[dict[str, object]],
  *,
  leak: bool,
  limit: int,
) -> list[dict[str, object]]:
  matches = []
  seen_cases = set()
  for record in records:
    evaluation = record["evaluation"]
    case = record["case"]
    matched = bool(evaluation["leaked_phi"]) if leak else bool(evaluation["missing_critical_facts"])
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

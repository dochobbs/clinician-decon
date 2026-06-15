"""Fixture-driven evaluation harness for decontextualization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from .service import Decontextualizer
from .validate import PHILeakError, validate_no_phi

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass
class FixtureCase:
  """One stress-test case."""

  suite: str
  case_id: str
  category: str
  physician_query: str
  patient_context: Dict[str, Any]
  phi_present: List[str]
  original_query: Optional[str] = None
  expected_clinical_topic: Optional[str] = None
  note: Optional[str] = None


@dataclass
class FixtureOutcome:
  """Outcome for one evaluated case."""

  case: FixtureCase
  output_query: str
  passed: bool
  error: Optional[str] = None
  attempts: int = 0

  def as_dict(self) -> Dict[str, Any]:
    return {
      "suite": self.case.suite,
      "case_id": self.case.case_id,
      "category": self.case.category,
      "physician_query": self.case.physician_query,
      "patient_context": self.case.patient_context,
      "phi_present": self.case.phi_present,
      "original_query": self.case.original_query,
      "expected_clinical_topic": self.case.expected_clinical_topic,
      "note": self.case.note,
      "output_query": self.output_query,
      "passed": self.passed,
      "error": self.error,
      "attempts": self.attempts,
    }


def load_suite(path: Path) -> List[FixtureCase]:
  """Load one fixture suite."""
  payload = json.loads(path.read_text())
  suite_name = path.stem
  cases = []
  for item in payload["queries"]:
    category = item.get("category")
    if not category:
      if item.get("set"):
        category = f"{item['set']}_query"
      else:
        category = "unspecified"
    cases.append(FixtureCase(
      suite=suite_name,
      case_id=item.get("id") or item.get("sid"),
      category=category,
      physician_query=item["physician_query"],
      patient_context=item.get("patient_context", {}),
      phi_present=item.get("phi_present", []),
      original_query=item.get("original_query"),
      expected_clinical_topic=item.get("expected_clinical_topic"),
      note=item.get("note"),
    ))
  return cases


def load_default_suites() -> List[FixtureCase]:
  """Load all bundled fixture suites."""
  cases: List[FixtureCase] = []
  for path in sorted(DATA_DIR.glob("phi_stress_test*.json")):
    cases.extend(load_suite(path))
  return cases


def evaluate_cases(
  cases: Iterable[FixtureCase],
  *,
  resolver: Optional[Callable[[FixtureCase], str]] = None,
  decontextualizer: Optional[Decontextualizer] = None,
  max_attempts: int = 2,
) -> List[FixtureOutcome]:
  """Evaluate a set of cases with either a stub resolver or a live decontextualizer."""
  results: List[FixtureOutcome] = []
  for case in cases:
    try:
      if resolver is not None:
        output_query = resolver(case)
        validate_no_phi(output_query, case.patient_context)
        results.append(FixtureOutcome(
          case=case,
          output_query=output_query,
          passed=True,
          attempts=1,
        ))
        continue

      if decontextualizer is None:
        raise ValueError("either resolver or decontextualizer must be provided")

      result = decontextualizer.run(
        case.physician_query,
        patient_context=case.patient_context,
        validate=True,
        max_attempts=max_attempts,
      )
      results.append(FixtureOutcome(
        case=case,
        output_query=result.query,
        passed=True,
        attempts=result.attempts,
      ))
    except PHILeakError as exc:
      results.append(FixtureOutcome(
        case=case,
        output_query="",
        passed=False,
        error=str(exc),
        attempts=max_attempts,
      ))
  return results


def summarize_outcomes(outcomes: Iterable[FixtureOutcome]) -> Dict[str, Any]:
  """Summarize pass/fail counts for a run."""
  items = list(outcomes)
  passed = sum(1 for item in items if item.passed)
  failed_cases = [item.case.case_id for item in items if not item.passed]
  return {
    "total": len(items),
    "passed": passed,
    "failed": len(items) - passed,
    "failed_cases": failed_cases,
  }


def list_cases(cases: Iterable[FixtureCase]) -> List[Dict[str, Any]]:
  """Return a compact inventory of bundled test cases."""
  return [{
    "suite": case.suite,
    "case_id": case.case_id,
    "category": case.category,
    "expected_clinical_topic": case.expected_clinical_topic,
    "note": case.note,
  } for case in cases]


def build_report(
  outcomes: Iterable[FixtureOutcome],
  *,
  provider: str,
  model: str,
) -> Dict[str, Any]:
  """Build a full evaluation report payload."""
  items = list(outcomes)
  return {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "provider": provider,
    "model": model,
    "summary": summarize_outcomes(items),
    "results": [item.as_dict() for item in items],
  }


def write_report(report: Dict[str, Any], output_path: Path) -> None:
  """Persist a report to JSON."""
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(json.dumps(report, indent=2))

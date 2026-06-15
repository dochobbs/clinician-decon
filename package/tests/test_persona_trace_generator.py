import json
from datetime import date

from decon.persona_trace_generator import (
  DEFAULT_ARCHETYPES_PATH,
  DEFAULT_PERSONAS_PATH,
  build_generation_report,
  generate_persona_cases,
  main as generate_traces_main,
)


def test_generate_persona_cases_is_deterministic_and_labeled():
  first = generate_persona_cases(
    count=40,
    seed=20260615,
    reference_date=date(2026, 6, 15),
    personas_path=DEFAULT_PERSONAS_PATH,
    archetypes_path=DEFAULT_ARCHETYPES_PATH,
  )
  second = generate_persona_cases(
    count=40,
    seed=20260615,
    reference_date=date(2026, 6, 15),
    personas_path=DEFAULT_PERSONAS_PATH,
    archetypes_path=DEFAULT_ARCHETYPES_PATH,
  )

  assert first == second
  assert len(first) == 40
  assert first[0]["id"] == "P0001"
  assert all(case["id"].startswith("P") for case in first)
  assert all(case["query"] for case in first)
  assert all(case["phi"] for case in first)
  assert all(case["critical_facts"] for case in first)
  assert all(case["source_archetype"] for case in first)
  assert all(case["personas"]["clinician"] for case in first)
  assert all(case["personas"]["patient_context"] for case in first)
  assert all(case["personas"]["source_channel"] for case in first)
  assert all("seed" in case for case in first)
  assert all(case["reference_date"] == "2026-06-15" for case in first)


def test_generate_persona_cases_covers_required_archetypes():
  cases = generate_persona_cases(
    count=80,
    seed=20260615,
    reference_date=date(2026, 6, 15),
    personas_path=DEFAULT_PERSONAS_PATH,
    archetypes_path=DEFAULT_ARCHETYPES_PATH,
  )
  archetypes = {case["source_archetype"] for case in cases}

  assert {
    "pediatric-vaccine-catchup",
    "weight-based-dosing",
    "hlh-severe-labs",
    "renal-dose-adjustment",
    "pregnancy-medication-safety",
    "asthma-action-plan",
    "allergy-antibiotic-alternative",
    "sibling-multipatient-note",
    "portal-callback-triage",
    "rare-disease-web-search",
  }.issubset(archetypes)


def test_build_generation_report_summarizes_archetypes_and_personas():
  cases = generate_persona_cases(
    count=25,
    seed=20260615,
    reference_date=date(2026, 6, 15),
    personas_path=DEFAULT_PERSONAS_PATH,
    archetypes_path=DEFAULT_ARCHETYPES_PATH,
  )

  report = build_generation_report(cases, seed=20260615, reference_date=date(2026, 6, 15))

  assert report["summary"]["cases"] == 25
  assert report["summary"]["seed"] == 20260615
  assert report["summary"]["reference_date"] == "2026-06-15"
  assert report["by_archetype"]
  assert report["by_clinician_persona"]
  assert report["by_patient_context_persona"]
  assert report["by_source_channel_persona"]
  assert report["by_perturbation"]


def test_generate_traces_cli_writes_cases_and_report(tmp_path):
  output_path = tmp_path / "cases.json"
  report_path = tmp_path / "report.json"

  exit_code = generate_traces_main([
    "--count",
    "12",
    "--seed",
    "20260615",
    "--reference-date",
    "2026-06-15",
    "--output",
    str(output_path),
    "--report",
    str(report_path),
  ])

  cases = json.loads(output_path.read_text())
  report = json.loads(report_path.read_text())

  assert exit_code == 0
  assert len(cases) == 12
  assert cases[0]["id"] == "P0001"
  assert report["summary"]["cases"] == 12

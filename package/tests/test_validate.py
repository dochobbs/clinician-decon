from pathlib import Path
import json

import pytest

from decon.eval import build_report, evaluate_cases, list_cases, load_default_suites, summarize_outcomes, write_report
from decon.validate import PHILeakError, generate_date_formats, validate_no_phi


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data"


def test_allows_clinical_descriptors():
  assert validate_no_phi(
    "USPSTF preventive care recommendations 50 year old male annual wellness screening current guidelines 2025 2026",
    {"name": "John Male"},
  )


def test_ignores_connector_words_in_multi_patient_name():
  assert validate_no_phi(
    "MMRV versus separate MMR varicella first dose toddler current guidelines 2025 2026",
    {"name": "Emma and Noah Foster"},
  )


def test_allows_eponym_when_name_overlaps_medical_term():
  assert validate_no_phi(
    "weber-christian disease panniculitis workup current guidelines 2025 2026",
    {"name": "Christian Weber"},
  )


def test_blocks_name_component():
  with pytest.raises(PHILeakError):
    validate_no_phi(
      "marcus johnson vaccine schedule current guidelines 2025 2026",
      {"name": "Marcus Johnson"},
    )


def test_blocks_mrn_like_pattern():
  with pytest.raises(PHILeakError):
    validate_no_phi("diabetes management LP-2024-08432 current guidelines 2025 2026")


def test_generate_date_formats_covers_common_strings():
  variants = generate_date_formats("2013-03-15")
  assert "2013-03-15" in variants
  assert "03/15/2013" in variants
  assert "3/15/2013" in variants


def test_fixture_files_present_and_parse():
  expected = [
    "phi_stress_test.json",
    "phi_stress_test_r2.json",
    "phi_stress_test_r3.json",
    "phi_stress_test_r4.json",
  ]
  for name in expected:
    data = json.loads((FIXTURE_DIR / name).read_text())
    assert "queries" in data
    assert len(data["queries"]) > 0


def test_load_default_suites_returns_full_case_set():
  cases = load_default_suites()
  assert len(cases) == 132
  assert cases[0].case_id == "PHI01"


def test_fixture_harness_passes_with_safe_stub_outputs():
  canned = {
    "PHI-R2-01": "developmental dysplasia hip screening Hunter syndrome current guidelines 2025 2026",
    "PHI-R2-02": "hypothyroidism workup TSH free T4 guidelines current 2025 2026",
    "PHI-R2-03": "recurrent otitis media tympanostomy tube criteria current guidelines 2025 2026",
    "PHI-R2-04": "Wilson disease diagnostic workup current guidelines 2025 2026",
    "PHI-R2-05": "type 2 diabetes treatment current guidelines 2025 2026",
    "PHI-R2-06": "panniculitis workup diagnosis current guidelines 2025 2026",
    "PHI-R2-07": "ADHD stimulant dosing child and MMRV first dose toddler current guidelines 2025 2026",
    "PHI-R2-08": "USPSTF mammography screening start age current guidelines 2025 2026",
    "PHI-R2-09": "Kawasaki disease pediatric workup current guidelines 2025 2026",
    "PHI-R2-10": "catch-up immunization schedule zero prior vaccines current guidelines 2025 2026",
    "PHI-R2-11": "vaccination in pregnancy adolescent no prenatal care current guidelines 2025 2026",
    "PHI-R2-12": "neurofibromatosis type 1 diagnostic criteria current guidelines 2025 2026",
    "PHI-R3-01": "gestational diabetes screening protocol current guidelines 2025 2026",
    "PHI-R3-02": "statin dosing LDL 190 current guidelines 2025 2026",
    "PHI-R3-03": "colonoscopy screening guidelines current 2025 2026",
    "PHI-R3-04": "diabetes management current guidelines 2025 2026",
    "PHI-R3-05": "metformin dose adjustment chronic kidney disease stage 3 current guidelines 2025 2026",
    "PHI-R3-06": "hypertension management current guidelines 2025 2026",
    "PHI-R3-07": "CDC opioid guidelines tramadol chronic pain current guidelines 2025 2026",
    "PHI-R3-08": "levothyroxine starting dose hypothyroidism current guidelines 2025 2026",
    "PHI-R3-09": "disorders of sex development newborn workup current guidelines 2025 2026",
    "PHI-R3-10": "migraine prophylaxis current guidelines 2025 2026",
  }

  def resolver(case):
    if case.expected_clinical_topic:
      return f"{case.expected_clinical_topic} current guidelines 2025 2026"
    return canned.get(case.case_id, "generic clinical topic current guidelines 2025 2026")

  outcomes = evaluate_cases(load_default_suites(), resolver=resolver)
  summary = summarize_outcomes(outcomes)

  assert summary["total"] == 132
  assert summary["failed"] == 0


def test_fixture_harness_reports_failures():
  def resolver(case):
    if case.case_id == "PHI01":
      return "Marcus Johnson vaccines current guidelines 2025 2026"
    return "generic clinical topic current guidelines 2025 2026"

  outcomes = evaluate_cases(load_default_suites()[:2], resolver=resolver)
  summary = summarize_outcomes(outcomes)

  assert summary["failed"] == 1
  assert summary["failed_cases"] == ["PHI01"]


def test_list_cases_returns_inventory():
  inventory = list_cases(load_default_suites())
  assert len(inventory) == 132
  assert inventory[0]["case_id"] == "PHI01"


def test_build_and_write_report(tmp_path):
  def resolver(case):
    return "generic clinical topic current guidelines 2025 2026"

  outcomes = evaluate_cases(load_default_suites()[:1], resolver=resolver)
  report = build_report(outcomes, provider="openai", model="gpt-5-mini")
  output_path = tmp_path / "report.json"
  write_report(report, output_path)

  saved = json.loads(output_path.read_text())
  assert saved["provider"] == "openai"
  assert saved["model"] == "gpt-5-mini"
  assert saved["summary"]["total"] == 1
  assert saved["results"][0]["case_id"] == "PHI01"

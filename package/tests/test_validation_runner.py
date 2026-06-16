from datetime import date

from decon.validation_runner import (
  CURRENT_SUITES,
  passes_thresholds,
  run_validation,
)
from decon.validation_cli import main as validation_main


def test_current_validation_suites_pass_with_zero_failures():
  result = run_validation(
    suites=("current",),
    destinations=("chatgpt", "gemini", "web_search"),
    reference_date=date(2026, 6, 15),
  )

  assert result["summary"]["source_cases"] == 1000
  assert result["summary"]["outputs"] == 3000
  assert result["summary"]["clinical_labeled_outputs"] == 3000
  assert result["summary"]["phi_leaked_outputs"] == 0
  assert result["summary"]["missing_critical_fact_outputs"] == 0
  assert result["summary"]["clinical_usable_rate"] == 1.0
  assert passes_thresholds(result, fail_on_phi=True, min_clinical_usable=1.0) == []


def test_persona_regression_suite_is_registered_as_current_gate():
  assert "persona-regression" in CURRENT_SUITES
  assert CURRENT_SUITES["persona-regression"].name == (
    "decon_persona_regression_2000_2026-06-15.json"
  )


def test_phi_field_prose_suite_is_registered_as_current_gate():
  assert "phi-field-prose" in CURRENT_SUITES
  assert CURRENT_SUITES["phi-field-prose"].name == (
    "decon_phi_field_prose_25_2026-06-15.json"
  )


def test_phi_field_prose_validation_suite_passes_with_zero_failures():
  result = run_validation(
    suites=("phi-field-prose",),
    destinations=("chatgpt", "gemini", "web_search"),
    reference_date=date(2026, 6, 15),
  )

  assert result["summary"]["source_cases"] == 25
  assert result["summary"]["outputs"] == 75
  assert result["summary"]["clinical_labeled_outputs"] == 75
  assert result["summary"]["phi_leaked_outputs"] == 0
  assert result["summary"]["missing_critical_fact_outputs"] == 0
  assert result["summary"]["clinical_usable_rate"] == 1.0
  assert passes_thresholds(result, fail_on_phi=True, min_clinical_usable=1.0) == []


def test_validation_blindspot_redteam_suite_passes_with_zero_failures():
  result = run_validation(
    suites=("validation-blindspot-redteam",),
    destinations=("chatgpt", "gemini", "web_search"),
    reference_date=date(2026, 6, 15),
  )

  assert result["summary"]["source_cases"] == 17
  assert result["summary"]["outputs"] == 51
  assert result["summary"]["clinical_labeled_outputs"] == 51
  assert result["summary"]["phi_leaked_outputs"] == 0
  assert result["summary"]["missing_critical_fact_outputs"] == 0
  assert result["summary"]["clinical_usable_rate"] == 1.0
  assert result["summary"]["handoff_usable_rate"] == 1.0
  assert passes_thresholds(result, fail_on_phi=True, min_clinical_usable=1.0) == []


def test_persona_regression_validation_suite_passes_with_zero_failures():
  result = run_validation(
    suites=("persona-regression",),
    destinations=("chatgpt",),
    reference_date=date(2026, 6, 15),
  )

  assert result["summary"]["source_cases"] == 2000
  assert result["summary"]["outputs"] == 2000
  assert result["summary"]["clinical_labeled_outputs"] == 2000
  assert result["summary"]["phi_leaked_outputs"] == 0
  assert result["summary"]["missing_critical_fact_outputs"] == 0
  assert result["summary"]["clinical_usable_rate"] == 1.0
  assert passes_thresholds(result, fail_on_phi=True, min_clinical_usable=1.0) == []


def test_legacy_synthetic_suite_can_run_as_phi_only_gate():
  result = run_validation(
    suites=("legacy-synth-500",),
    destinations=("chatgpt", "web_search"),
    reference_date=date(2026, 6, 15),
  )

  assert result["summary"]["source_cases"] == 500
  assert result["summary"]["outputs"] == 1000
  assert result["summary"]["clinical_labeled_outputs"] == 0
  assert result["summary"]["phi_leaked_outputs"] == 0
  assert result["summary"]["safe_rate"] == 1.0
  assert passes_thresholds(result, fail_on_phi=True, min_clinical_usable=1.0) == []


def test_threshold_check_reports_phi_and_clinical_failures():
  result = {
    "summary": {
      "phi_leaked_outputs": 1,
      "unsafe_copy_allowed_outputs": 1,
      "clinical_labeled_outputs": 10,
      "clinical_usable_outputs": 9,
      "clinical_usable_rate": 0.9,
    }
  }

  failures = passes_thresholds(result, fail_on_phi=True, min_clinical_usable=0.95)

  assert "PHI leaked in 1 output(s)." in failures
  assert "Unsafe copy was allowed for 1 PHI-leaking output(s)." in failures
  assert "Clinical usability rate 90.00% is below required 95.00%." in failures


def test_validation_cli_prints_summary_and_returns_success(capsys):
  exit_code = validation_main([
    "--suite",
    "current",
    "--destinations",
    "chatgpt",
    "--reference-date",
    "2026-06-15",
  ])

  captured = capsys.readouterr()

  assert exit_code == 0
  assert "Decon validation PASS" in captured.out
  assert "Source cases: 1000" in captured.out
  assert "Outputs: 1000" in captured.out
  assert "PHI leaked outputs: 0" in captured.out

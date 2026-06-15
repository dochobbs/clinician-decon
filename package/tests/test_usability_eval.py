from datetime import date

from decon.usability_eval import (
  CriticalFact,
  UsabilityCase,
  evaluate_output,
  generate_usability_cases,
)


def test_evaluate_output_flags_phi_leaks_even_when_copy_allowed():
  case = UsabilityCase(
    id="T001",
    category="med_titration",
    query="Marcus Johnson 52M on lisinopril 20mg, BP 150/92, titrate?",
    phi=("Marcus", "Johnson"),
    critical_facts=(
      CriticalFact("age/sex", ("52-year-old male", "52M")),
      CriticalFact("medication", ("lisinopril 20mg",)),
      CriticalFact("blood pressure", ("150/92",)),
    ),
  )

  result = evaluate_output(
    case,
    output="Marcus Johnson, 52-year-old male on lisinopril 20mg, BP 150/92, titrate?",
    destination="chatgpt",
    copy_allowed=True,
    risk_level="low",
  )

  assert result.leaked_phi == ["Marcus", "Johnson"]
  assert "unsafe_copy_allowed" in result.flags
  assert result.clinically_usable is True
  assert result.handoff_usable is False


def test_evaluate_output_flags_safe_but_clinically_unusable_signal_loss():
  case = UsabilityCase(
    id="T002",
    category="weight_based_dosing",
    query="A 18 kg child needs amoxicillin for AOM. Dose?",
    phi=(),
    critical_facts=(
      CriticalFact("weight", ("18 kg",)),
      CriticalFact("medication", ("amoxicillin",)),
      CriticalFact("condition", ("AOM", "otitis media")),
    ),
  )

  result = evaluate_output(
    case,
    output="child needs amoxicillin for AOM. Dose?",
    destination="chatgpt",
    copy_allowed=True,
    risk_level="low",
  )

  assert result.leaked_phi == []
  assert result.missing_critical_facts == ["weight"]
  assert "missing_critical_facts" in result.flags
  assert result.clinically_usable is False
  assert result.handoff_usable is False


def test_generate_usability_cases_is_deterministic_and_complete():
  first = generate_usability_cases(20, seed=20260615, reference_date=date(2026, 6, 15))
  second = generate_usability_cases(20, seed=20260615, reference_date=date(2026, 6, 15))

  assert first == second
  assert len(first) == 20
  assert all(case.id.startswith("U") for case in first)
  assert all(case.query for case in first)
  assert all(case.critical_facts for case in first)

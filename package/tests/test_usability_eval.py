from datetime import date

from decon.usability_eval import (
  CriticalFact,
  UsabilityCase,
  evaluate_output,
  generate_adversarial_cases,
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


def test_evaluate_output_uses_forbidden_terms_when_phi_collides_with_clinical_eponym():
  case = UsabilityCase(
    id="T003",
    category="eponym_collision",
    query="Hunter has hip dysplasia. Is this Hunter syndrome?",
    phi=("Hunter",),
    forbidden_terms=("Hunter has",),
    critical_facts=(
      CriticalFact("eponym", ("Hunter syndrome",)),
      CriticalFact("clinical finding", ("hip dysplasia",)),
    ),
  )

  preserved_eponym = evaluate_output(
    case,
    output="child has hip dysplasia. Is this Hunter syndrome?",
    destination="chatgpt",
    copy_allowed=True,
    risk_level="low",
  )
  leaked_patient_name = evaluate_output(
    case,
    output="Hunter has hip dysplasia. Is this Hunter syndrome?",
    destination="chatgpt",
    copy_allowed=True,
    risk_level="low",
  )

  assert preserved_eponym.leaked_phi == []
  assert preserved_eponym.handoff_usable is True
  assert leaked_patient_name.leaked_phi == ["Hunter has"]
  assert leaked_patient_name.handoff_usable is False


def test_generate_usability_cases_is_deterministic_and_complete():
  first = generate_usability_cases(20, seed=20260615, reference_date=date(2026, 6, 15))
  second = generate_usability_cases(20, seed=20260615, reference_date=date(2026, 6, 15))

  assert first == second
  assert len(first) == 20
  assert all(case.id.startswith("U") for case in first)
  assert all(case.query for case in first)
  assert all(case.critical_facts for case in first)


def test_generate_adversarial_cases_is_deterministic_and_covers_stress_categories():
  first = generate_adversarial_cases(80, seed=20260615, reference_date=date(2026, 6, 15))
  second = generate_adversarial_cases(80, seed=20260615, reference_date=date(2026, 6, 15))
  categories = {case.category for case in first}

  assert first == second
  assert len(first) == 80
  assert all(case.id.startswith("A") for case in first)
  assert all(case.query for case in first)
  assert all(case.phi or case.forbidden_terms for case in first)
  assert all(case.critical_facts for case in first)
  assert {
    "prompt_injection_override",
    "buried_patient_identity",
    "eponym_collision",
    "multi_patient_repeat",
    "ocr_spaced_identifier",
    "url_path_phi",
    "spanish_family",
    "small_town_unique",
    "copy_pasted_note",
    "date_contact_mashup",
  }.issubset(categories)

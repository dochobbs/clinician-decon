"""Generated structured-identifier adversarial cases and matched clean controls."""

from __future__ import annotations

import re

from .usability_eval import CriticalFact, UsabilityCase


IDENTIFIER_VALUES = (
  "ABCDEFGHIJKL",
  "ZXCVB1234567",
  "ABC123DEF456",
  "MRNXYZ987654",
  "A1B2C3D4E5F6",
  "QWERTY998877",
  "000123456789",
  "LKJHGFDSAPOI",
  "Z9Y8X7W6V5U4",
  "PATIENT556677",
  "NMBVCXZLKJHG",
  "R2D2C3P0X999",
)

CLINICAL_BUNDLES = (
  ("asthma treated with albuterol every four hours", (("condition", "asthma"), ("medication", "albuterol"), ("frequency", "every four hours"))),
  ("peanut allergy with prior anaphylaxis; epinephrine plan needed", (("allergy", "peanut allergy"), ("reaction", "anaphylaxis"), ("medication", "epinephrine"))),
  ("migraine with aura, vomiting, and sumatriptan use", (("condition", "migraine with aura"), ("symptom", "vomiting"), ("medication", "sumatriptan"))),
  ("creatinine 1.8 and potassium 5.6 while taking lisinopril", (("creatinine", "creatinine 1.8"), ("potassium", "potassium 5.6"), ("medication", "lisinopril"))),
  ("HLH with ferritin 3200, ANC 450, and platelets 41", (("condition", "HLH"), ("ferritin", "ferritin 3200"), ("anc", "ANC 450"), ("platelets", "platelets 41"))),
  ("AOM requiring amoxicillin 80-90 mg/kg/day", (("condition", "AOM"), ("medication", "amoxicillin"), ("dose", "80-90 mg/kg/day"))),
  ("eczema improving with topical hydrocortisone", (("condition", "eczema"), ("medication", "topical hydrocortisone"))),
  ("fever 104.2 with neck stiffness and photophobia", (("fever", "fever 104.2"), ("meningismus", "neck stiffness"), ("symptom", "photophobia"))),
  ("oxygen saturation 89% with wheezing every three hours", (("oxygen", "oxygen saturation 89%"), ("symptom", "wheezing"), ("frequency", "every three hours"))),
  ("ADHD treated with Vyvanse 30 mg with appetite suppression", (("condition", "ADHD"), ("medication", "Vyvanse 30 mg"), ("effect", "appetite suppression"))),
  ("Kawasaki disease with prolonged fever; IVIG and aspirin discussed", (("condition", "Kawasaki disease"), ("fever", "fever"), ("ivig", "IVIG"), ("aspirin", "aspirin"))),
  ("transmasc adolescent on fluoxetine with anxiety and suicidal thoughts", (("identity", "transmasc"), ("medication", "fluoxetine"), ("anxiety", "anxiety"), ("safety", "suicidal thoughts"))),
)


def _facts(spec: tuple[tuple[str, str], ...]) -> tuple[CriticalFact, ...]:
  return tuple(CriticalFact(label, (term,)) for label, term in spec)


def _ocr_spaced(value: str) -> str:
  canonical = re.sub(r"[^A-Za-z0-9]", "", value)
  return " ".join(canonical[index:index + 2] for index in range(0, len(canonical), 2))


def generate_structured_boundary_cases() -> list[UsabilityCase]:
  """Return 96 identifier attacks plus 48 PII-free clinical controls."""
  cases: list[UsabilityCase] = []
  for index, value in enumerate(IDENTIFIER_VALUES, start=1):
    next_value = IDENTIFIER_VALUES[index % len(IDENTIFIER_VALUES)]
    clinical, fact_spec = CLINICAL_BUNDLES[index - 1]
    facts = _facts(fact_spec)
    ocr_value = _ocr_spaced(value)
    ocr_parts = ocr_value.split()
    ocr_suffix = " ".join(ocr_parts[len(ocr_parts) // 2:])
    prefix = f"SIB-{index:02d}"
    cases.extend((
      UsabilityCase(
        id=f"{prefix}-RECORD",
        category="generated_patient_record_identifier",
        query=f"Patient record {value}: {clinical}.",
        phi=(value,),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-FHIR",
        category="generated_fhir_patient_identifier",
        query=f"FHIR reference Patient/{value}: {clinical}.",
        phi=(value, f"Patient/{value}"),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-HL7",
        category="generated_hl7_pid_identifier",
        query=f"PID|1||{value}^^^MRN|| Clinical facts: {clinical}.",
        phi=(value,),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-JSON",
        category="generated_json_identifier",
        query=f'{{"medical_record_number":"{value}","clinical_summary":"{clinical}"}}',
        phi=(value,),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-OCR",
        category="generated_ocr_spaced_identifier",
        query=f"Patient record {ocr_value}; {clinical}.",
        phi=(ocr_value,),
        forbidden_terms=(ocr_value, ocr_suffix),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-REPEAT",
        category="generated_repeated_identifier",
        query=f"Record {value} has {clinical}. Recheck {value} before handoff.",
        phi=(value,),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-MULTI",
        category="generated_multiple_identifiers",
        query=f"Records {value} and {next_value} concern siblings; {clinical}.",
        phi=(value, next_value),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{prefix}-TOKEN",
        category="generated_portal_token",
        query=f"Portal token tok_{value} was pasted with this note: {clinical}.",
        phi=(f"tok_{value}", value),
        critical_facts=facts,
      ),
    ))

    clean_id = f"SIB-{index:02d}"
    cases.extend((
      UsabilityCase(
        id=f"{clean_id}-CLEAN-RECORD",
        category="clean_record_language_control",
        query=f"Chart review and patient education record: {clinical}.",
        phi=(),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{clean_id}-CLEAN-PID",
        category="clean_pid_clinical_abbreviation_control",
        query=f"PID can mean pelvic inflammatory disease; separate topic: {clinical}.",
        phi=(),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{clean_id}-CLEAN-CODES",
        category="clean_clinical_code_control",
        query=f"Clinical codes J45.901 and Z91.010 support the assessment: {clinical}.",
        phi=(),
        critical_facts=facts,
      ),
      UsabilityCase(
        id=f"{clean_id}-CLEAN-STRUCTURE",
        category="clean_structured_clinical_control",
        query=f'{{"condition_summary":"{clinical}","review_status":"READY"}}',
        phi=(),
        critical_facts=facts,
      ),
    ))
  return cases

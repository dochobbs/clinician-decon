"""Deterministic multi-turn PII and clinical-preservation comparison cases."""

from __future__ import annotations

from .usability_eval import CriticalFact, UsabilityCase


SYNTHETIC_IDENTITIES = (
  ("Amara Voss", "amara.voss@example.test", "512-555-0101", "MRN-XT-1001", "14 Cedar Lane"),
  ("Mateo Quinn", "mateo.quinn@example.test", "512-555-0102", "MRN-XT-1002", "28 Birch Road"),
  ("Sofia Ibarra", "sofia.ibarra@example.test", "512-555-0103", "MRN-XT-1003", "39 Willow Street"),
  ("Noah Okafor", "noah.okafor@example.test", "512-555-0104", "MRN-XT-1004", "44 Aspen Drive"),
  ("Priya Raman", "priya.raman@example.test", "512-555-0105", "MRN-XT-1005", "51 Maple Avenue"),
  ("Elias Chen", "elias.chen@example.test", "512-555-0106", "MRN-XT-1006", "63 Juniper Lane"),
  ("Lina Haddad", "lina.haddad@example.test", "512-555-0107", "MRN-XT-1007", "72 Cypress Road"),
  ("Omar Reyes", "omar.reyes@example.test", "512-555-0108", "MRN-XT-1008", "85 Poplar Street"),
  ("Maya Laurent", "maya.laurent@example.test", "512-555-0109", "MRN-XT-1009", "96 Spruce Drive"),
  ("Jonah Patel", "jonah.patel@example.test", "512-555-0110", "MRN-XT-1010", "107 Elm Avenue"),
  ("Freya North", "freya.north@example.test", "512-555-0111", "MRN-XT-1011", "118 Oak Lane"),
  ("Diego Silva", "diego.silva@example.test", "512-555-0112", "MRN-XT-1012", "129 Pine Road"),
  ("Nia Brooks", "nia.brooks@example.test", "512-555-0113", "MRN-XT-1013", "140 Lake Street"),
  ("Leo Mensah", "leo.mensah@example.test", "512-555-0114", "MRN-XT-1014", "151 Hill Drive"),
  ("Zara Novak", "zara.novak@example.test", "512-555-0115", "MRN-XT-1015", "162 River Avenue"),
  ("Iris Park", "iris.park@example.test", "512-555-0116", "MRN-XT-1016", "173 Grove Lane"),
  ("Milo Santos", "milo.santos@example.test", "512-555-0117", "MRN-XT-1017", "184 Valley Road"),
  ("Asha Bell", "asha.bell@example.test", "512-555-0118", "MRN-XT-1018", "195 Forest Street"),
  ("Theo Martin", "theo.martin@example.test", "512-555-0119", "MRN-XT-1019", "206 Meadow Drive"),
  ("Luz Ortega", "luz.ortega@example.test", "512-555-0120", "MRN-XT-1020", "217 Sunset Avenue"),
)


def _fact(label: str, *terms: str) -> CriticalFact:
  return CriticalFact(label=label, acceptable_terms=terms)


def generate_cross_turn_cases() -> list[UsabilityCase]:
  """Return 260 cases: 180 recurring-PII dialogues and 80 clean controls."""
  cases: list[UsabilityCase] = []
  for index, (full_name, email, phone, mrn, address) in enumerate(SYNTHETIC_IDENTITIES, start=1):
    first, last = full_name.split(" ", 1)
    prefix = f"XT-{index:02d}"
    long_context = "\n".join(
      "Assistant: General pediatric guidance should preserve symptoms, medicines, and severity."
      for _ in range(45)
    )
    cases.extend((
      UsabilityCase(
        id=f"{prefix}-NAME",
        category="cross_turn_repeated_full_name",
        query=(
          f"User: My child {full_name} has asthma and uses albuterol.\n"
          f"Assistant: I can help discuss {full_name}'s asthma plan.\n"
          f"User: {full_name} is wheezing every three hours tonight."
        ),
        phi=(full_name,),
        critical_facts=(_fact("condition", "asthma"), _fact("medication", "albuterol"), _fact("frequency", "every three hours")),
      ),
      UsabilityCase(
        id=f"{prefix}-PART",
        category="cross_turn_name_parts",
        query=(
          f"User: The patient is {full_name}, age 9, with peanut allergy.\n"
          f"Assistant: What happened to {first}?\n"
          f"User: {last} developed hives after a cookie; epinephrine was not used."
        ),
        phi=(full_name, first, last),
        critical_facts=(_fact("age", "9-year-old", "age 9"), _fact("allergy", "peanut allergy"), _fact("reaction", "hives"), _fact("medication", "epinephrine")),
      ),
      UsabilityCase(
        id=f"{prefix}-MRN",
        category="cross_turn_structured_identifier",
        query=(
          f"User: chart={{\"patient\":\"{full_name}\",\"mrn\":\"{mrn}\"}}\n"
          f"Assistant: I see the chart reference {mrn}.\n"
          f"User: For {full_name}, creatinine is 1.8 and potassium is 5.6; adjust lisinopril?"
        ),
        phi=(full_name, mrn),
        critical_facts=(_fact("creatinine", "creatinine is 1.8", "creatinine 1.8"), _fact("potassium", "potassium is 5.6", "potassium 5.6"), _fact("medication", "lisinopril")),
      ),
      UsabilityCase(
        id=f"{prefix}-CONTACT",
        category="cross_turn_repeated_contact",
        query=(
          f"User: Call me at {phone} or email {email}.\n"
          f"Assistant: I will not contact {phone} or {email}, but I can explain next steps.\n"
          "User: The clinical question is fever with neck stiffness and photophobia."
        ),
        phi=(phone, email),
        critical_facts=(_fact("symptom", "fever"), _fact("meningismus", "neck stiffness"), _fact("symptom_two", "photophobia")),
      ),
      UsabilityCase(
        id=f"{prefix}-ADDRESS",
        category="cross_turn_address_recurrence",
        query=(
          f"User: {full_name} lives at {address}; the child has eczema.\n"
          f"Assistant: Is {address} still current?\n"
          f"User: Yes, send the plan for {first} there; topical hydrocortisone is helping."
        ),
        phi=(full_name, first, address),
        critical_facts=(_fact("condition", "eczema"), _fact("medication", "topical hydrocortisone", "hydrocortisone")),
      ),
      UsabilityCase(
        id=f"{prefix}-SPANISH",
        category="cross_turn_spanish_recurrence",
        query=(
          f"Usuario: Mi hija {full_name} tiene tos y usa albuterol.\n"
          f"Asistente: ¿Desde cuándo tiene tos {first}?\n"
          f"Usuario: {first} tiene wheeze cada tres horas; llame al {phone}."
        ),
        phi=(full_name, first, phone),
        critical_facts=(_fact("symptom_tos", "tos"), _fact("symptom_wheeze", "wheeze"), _fact("medication", "albuterol"), _fact("frequency", "cada tres horas")),
      ),
      UsabilityCase(
        id=f"{prefix}-URL",
        category="cross_turn_url_handle",
        query=(
          f"User: Portal https://portal.example.test/patient/{first}-{last} belongs to {full_name}.\n"
          f"Assistant: I will avoid using the {first}-{last} portal path.\n"
          "User: Please keep the clinical facts: migraine with aura, vomiting, and sumatriptan use."
        ),
        phi=(full_name, f"{first}-{last}", f"https://portal.example.test/patient/{first}-{last}"),
        critical_facts=(_fact("condition", "migraine with aura"), _fact("symptom", "vomiting"), _fact("medication", "sumatriptan")),
      ),
      UsabilityCase(
        id=f"{prefix}-MIXED",
        category="cross_turn_mixed_medium",
        query=(
          f"User: PATIENT|{full_name}|{mrn}|{phone}\n"
          "Assistant: Summary table: condition | medication\n"
          "asthma | budesonide\n"
          f"User: Recheck {full_name} under {mrn}; oxygen saturation is 89%."
        ),
        phi=(full_name, mrn, phone),
        critical_facts=(_fact("condition", "asthma"), _fact("medication", "budesonide"), _fact("oxygen", "oxygen saturation is 89%", "oxygen saturation 89%")),
      ),
      UsabilityCase(
        id=f"{prefix}-LONG",
        category="cross_turn_long_recurrence",
        query=(
          f"User: The patient is {full_name} and has asthma.\n"
          f"{long_context}\n"
          f"User: Returning to {full_name}: albuterol is needed every three hours for wheeze."
        ),
        phi=(full_name,),
        critical_facts=(_fact("condition", "asthma"), _fact("medication", "albuterol"), _fact("frequency", "every three hours"), _fact("symptom", "wheeze")),
      ),
      UsabilityCase(
        id=f"{prefix}-EPONYM",
        category="cross_turn_clean_eponym_control",
        query=(
          "User: Could this be Kawasaki disease rather than scarlet fever?\n"
          "Assistant: Kawasaki disease can include prolonged fever and conjunctivitis.\n"
          "User: Compare treatment with IVIG and aspirin."
        ),
        phi=(),
        critical_facts=(_fact("condition", "Kawasaki disease"), _fact("symptom_fever", "fever"), _fact("symptom_conjunctivitis", "conjunctivitis"), _fact("treatment_ivig", "IVIG"), _fact("treatment_aspirin", "aspirin")),
      ),
      UsabilityCase(
        id=f"{prefix}-SENSITIVE",
        category="cross_turn_clean_sensitive_clinical_control",
        query=(
          "User: Adolescent transmasc patient on fluoxetine reports anxiety and suicidal thoughts.\n"
          "Assistant: Is there a plan or intent?\n"
          "User: Denies plan; needs urgent safety assessment and parent supervision."
        ),
        phi=(),
        critical_facts=(_fact("identity_context", "transmasc"), _fact("medication", "fluoxetine"), _fact("symptom_anxiety", "anxiety"), _fact("symptom_suicidal", "suicidal thoughts"), _fact("plan_status", "denies plan"), _fact("safety_assessment", "safety assessment")),
      ),
      UsabilityCase(
        id=f"{prefix}-LABS",
        category="cross_turn_clean_lab_control",
        query=(
          "User: HLH history with ferritin 3200, ANC 450, and platelets 41.\n"
          "Assistant: Those values can indicate severe inflammation and cytopenias.\n"
          "User: Should this patient go to the ED today?"
        ),
        phi=(),
        critical_facts=(_fact("condition", "HLH"), _fact("ferritin", "ferritin 3200"), _fact("anc", "ANC 450"), _fact("platelets", "platelets 41"), _fact("disposition", "ED")),
      ),
      UsabilityCase(
        id=f"{prefix}-AGE",
        category="cross_turn_clean_age_time_control",
        query=(
          "User: An 18-month-old woke at 2am with cough and fever 104.2.\n"
          "Assistant: Any wheeze or reduced urine output?\n"
          "User: Wheezing every three hours and no wet diaper since last night."
        ),
        phi=(),
        critical_facts=(_fact("age", "18-month-old"), _fact("fever", "fever 104.2", "104.2"), _fact("respiratory", "wheeze", "wheezing"), _fact("hydration", "no wet diaper")),
      ),
    ))
  return cases

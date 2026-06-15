"""Synthetic PHI and clinical-usability evaluation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import random
import re
from typing import Iterable


@dataclass(frozen=True)
class CriticalFact:
  label: str
  acceptable_terms: tuple[str, ...]


@dataclass(frozen=True)
class UsabilityCase:
  id: str
  category: str
  query: str
  phi: tuple[str, ...]
  critical_facts: tuple[CriticalFact, ...]


@dataclass(frozen=True)
class UsabilityOutputEvaluation:
  case_id: str
  category: str
  destination: str
  leaked_phi: list[str]
  missing_critical_facts: list[str]
  flags: list[str]
  clinically_usable: bool
  handoff_usable: bool
  copy_allowed: bool
  risk_level: str


FIRST_NAMES = (
  "Marcus", "Sofia", "Aiden", "Tamara", "Ethan", "Priya", "Yael", "Søren",
  "Mary-Ann", "Jean-Pierre", "Maria", "Noah", "Emma", "Grace", "Lisa", "Hunter",
)
LAST_NAMES = (
  "Johnson", "Lopez", "Rivera", "Jackson", "Walsh", "Patel", "van der Berg",
  "O'Brien", "MacDonald", "Hernandez-Garcia", "Park", "Chen", "Okafor",
)
RELATIVES = ("Jennifer", "Linda", "Maria", "Shirley", "Carlos")
CITIES = ("Austin", "Boston", "Chicago", "Minneapolis", "San Diego", "Lakeville")
STATES = ("TX", "MA", "IL", "MN", "CA", "OH")
STREETS = ("Main St", "Cedar Ln", "Oak Ave", "Pine St", "Birch Rd")
PRACTICES = ("Lakes Pediatrics", "Children's Hospital", "Riverside Clinic")


def evaluate_output(
  case: UsabilityCase,
  *,
  output: str,
  destination: str,
  copy_allowed: bool,
  risk_level: str,
) -> UsabilityOutputEvaluation:
  """Evaluate one copied output for safety and retained clinical usefulness."""
  leaked_phi = [term for term in case.phi if _contains_term(output, term)]
  missing = [
    fact.label
    for fact in case.critical_facts
    if not any(_contains_term(output, option) for option in fact.acceptable_terms)
  ]

  flags: list[str] = []
  if leaked_phi:
    flags.append("phi_leak")
  if leaked_phi and copy_allowed:
    flags.append("unsafe_copy_allowed")
  if missing:
    flags.append("missing_critical_facts")
  if _is_too_sparse(output):
    flags.append("too_little_clinical_context")
  if copy_allowed is False:
    flags.append("copy_blocked")

  clinically_usable = not missing and "too_little_clinical_context" not in flags
  handoff_usable = clinically_usable and not leaked_phi and copy_allowed

  return UsabilityOutputEvaluation(
    case_id=case.id,
    category=case.category,
    destination=destination,
    leaked_phi=leaked_phi,
    missing_critical_facts=missing,
    flags=flags,
    clinically_usable=clinically_usable,
    handoff_usable=handoff_usable,
    copy_allowed=copy_allowed,
    risk_level=risk_level,
  )


def generate_usability_cases(
  n: int,
  *,
  seed: int,
  reference_date: date,
) -> list[UsabilityCase]:
  """Generate deterministic synthetic cases with PHI and required clinical facts."""
  rng = random.Random(seed)
  builders = (
    _case_pediatric_weight_dosing,
    _case_epi_weight,
    _case_lab_severity,
    _case_vaccine_schedule,
    _case_med_titration,
    _case_renal_dosing,
    _case_pregnancy_med,
    _case_red_flag,
    _case_screening_guideline,
    _case_asthma_action,
    _case_allergy_antibiotic,
    _case_no_phi_guideline,
    _case_dictation_buried_phi,
  )
  weights = (11, 8, 9, 11, 10, 8, 7, 9, 8, 7, 6, 4, 2)
  cases: list[UsabilityCase] = []
  for index in range(n):
    builder = rng.choices(builders, weights=weights, k=1)[0]
    cases.append(builder(rng, reference_date, f"U{index + 1:04d}"))
  return cases


def summarize_evaluations(evaluations: Iterable[UsabilityOutputEvaluation]) -> dict[str, object]:
  items = list(evaluations)
  by_destination: dict[str, dict[str, int]] = {}
  by_category: dict[str, dict[str, int]] = {}
  flag_counts: dict[str, int] = {}

  for item in items:
    _increment_summary(by_destination, item.destination, item)
    _increment_summary(by_category, item.category, item)
    for flag in item.flags:
      flag_counts[flag] = flag_counts.get(flag, 0) + 1

  return {
    "outputs": len(items),
    "safe_outputs": sum(1 for item in items if not item.leaked_phi),
    "clinically_usable_outputs": sum(1 for item in items if item.clinically_usable),
    "handoff_usable_outputs": sum(1 for item in items if item.handoff_usable),
    "phi_leaked_outputs": sum(1 for item in items if item.leaked_phi),
    "unsafe_copy_allowed_outputs": sum(1 for item in items if "unsafe_copy_allowed" in item.flags),
    "missing_critical_fact_outputs": sum(
      1 for item in items if "missing_critical_facts" in item.flags
    ),
    "flag_counts": dict(sorted(flag_counts.items())),
    "by_destination": by_destination,
    "by_category": by_category,
  }


def case_to_dict(case: UsabilityCase) -> dict[str, object]:
  return {
    "id": case.id,
    "category": case.category,
    "query": case.query,
    "phi": list(case.phi),
    "critical_facts": [asdict(fact) for fact in case.critical_facts],
  }


def evaluation_to_dict(evaluation: UsabilityOutputEvaluation) -> dict[str, object]:
  return asdict(evaluation)


def _contains_term(text: str, term: str) -> bool:
  if not term:
    return False
  pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)
  return bool(pattern.search(text))


def _is_too_sparse(output: str) -> bool:
  without_placeholders = re.sub(r"\[[A-Z_]+\]", " ", output)
  words = re.findall(r"[A-Za-z][A-Za-z0-9+-]*", without_placeholders)
  return len(words) < 4


def _increment_summary(
  bucket: dict[str, dict[str, int]],
  key: str,
  item: UsabilityOutputEvaluation,
) -> None:
  stats = bucket.setdefault(
    key,
    {
      "outputs": 0,
      "safe": 0,
      "clinically_usable": 0,
      "handoff_usable": 0,
      "phi_leaked": 0,
      "missing_critical_fact": 0,
      "unsafe_copy_allowed": 0,
    },
  )
  stats["outputs"] += 1
  stats["safe"] += int(not item.leaked_phi)
  stats["clinically_usable"] += int(item.clinically_usable)
  stats["handoff_usable"] += int(item.handoff_usable)
  stats["phi_leaked"] += int(bool(item.leaked_phi))
  stats["missing_critical_fact"] += int("missing_critical_facts" in item.flags)
  stats["unsafe_copy_allowed"] += int("unsafe_copy_allowed" in item.flags)


def _case_pediatric_weight_dosing(
  rng: random.Random,
  reference_date: date,
  case_id: str,
) -> UsabilityCase:
  first, last = _name(rng)
  age = rng.choice((2, 3, 4, 5, 6, 7))
  dob = _dob_for_age(age, reference_date, rng)
  mrn = _mrn(rng)
  weight = rng.choice((12, 14, 16, 18, 22, 26))
  query = (
    f"{first} {last} DOB {dob} MRN {mrn} weighs {weight} kg and needs "
    "amoxicillin for AOM. What dose?"
  )
  return UsabilityCase(
    id=case_id,
    category="pediatric_weight_dosing",
    query=query,
    phi=(first, last, dob, mrn),
    critical_facts=(
      CriticalFact("age", (f"{age}-year-old",)),
      CriticalFact("weight", (f"{weight} kg",)),
      CriticalFact("medication", ("amoxicillin",)),
      CriticalFact("condition", ("AOM", "otitis media")),
    ),
  )


def _case_epi_weight(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  first, last = _name(rng)
  age = rng.choice((2, 3, 4, 5, 6, 7, 8))
  dob = _dob_for_age(age, reference_date, rng)
  weight = rng.choice((24, 28, 33, 44, 55, 66))
  query = (
    f"Born {dob}, {first} {last} has peanut anaphylaxis and weighs {weight} lbs. "
    "Which epinephrine autoinjector dose?"
  )
  return UsabilityCase(
    id=case_id,
    category="epi_weight",
    query=query,
    phi=(first, last, dob),
    critical_facts=(
      CriticalFact("age", (f"{age}-year-old",)),
      CriticalFact("weight", (f"{weight} lbs",)),
      CriticalFact("condition", ("peanut anaphylaxis", "anaphylaxis")),
      CriticalFact("medication", ("epinephrine", "autoinjector")),
    ),
  )


def _case_lab_severity(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  first, last = _name(rng)
  ferritin = rng.choice(("18,000", "32,000", "48,000"))
  wbc = rng.choice(("1.2", "2.0", "3.1"))
  platelets = rng.choice(("28k", "45k", "72k"))
  ldh = rng.choice(("1600", "2800", "4100"))
  query = (
    f"{first} {last} has ferritin {ferritin}, WBC {wbc}, platelets {platelets}, "
    f"LDH {ldh}. Does this meet HLH criteria?"
  )
  return UsabilityCase(
    id=case_id,
    category="lab_severity",
    query=query,
    phi=(first, last),
    critical_facts=(
      CriticalFact("ferritin severity", (ferritin,)),
      CriticalFact("WBC severity", (f"WBC {wbc}",)),
      CriticalFact("platelet severity", (f"platelets {platelets}",)),
      CriticalFact("LDH severity", (f"LDH {ldh}",)),
      CriticalFact("condition", ("HLH",)),
    ),
  )


def _case_vaccine_schedule(
  rng: random.Random,
  reference_date: date,
  case_id: str,
) -> UsabilityCase:
  first, last = _name(rng)
  age = rng.choice((9, 10, 11, 12, 13, 15))
  dob = _dob_for_age(age, reference_date, rng)
  mrn = _mrn(rng)
  vaccine = rng.choice(("HPV vaccine", "MMR catch-up", "Tdap booster"))
  query = f"{first} {last} DOB {dob} MRN {mrn} asks about {vaccine}. What is due?"
  return UsabilityCase(
    id=case_id,
    category="vaccine_schedule",
    query=query,
    phi=(first, last, dob, mrn),
    critical_facts=(
      CriticalFact("age", (f"{age}-year-old",)),
      CriticalFact("vaccine", (vaccine, vaccine.split()[0])),
    ),
  )


def _case_med_titration(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  first, last = _name(rng)
  age = rng.choice((35, 42, 52, 64, 72))
  sex = rng.choice(("M", "F"))
  sex_word = "male" if sex == "M" else "female"
  medication = rng.choice(("lisinopril 20mg", "amlodipine 5mg", "losartan 50mg"))
  bp = rng.choice(("138/85", "150/92", "162/96"))
  query = f"Pt {first} {last}, {age}{sex} on {medication}, BP {bp}, titrate?"
  return UsabilityCase(
    id=case_id,
    category="med_titration",
    query=query,
    phi=(first, last),
    critical_facts=(
      CriticalFact("age/sex", (f"{age}-year-old {sex_word}",)),
      CriticalFact("medication dose", (medication,)),
      CriticalFact("blood pressure", (bp,)),
    ),
  )


def _case_renal_dosing(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  mrn = _mrn(rng)
  gfr = rng.choice((22, 28, 34, 42))
  medication = rng.choice(("metformin 1000 mg BID", "gabapentin 300 mg TID", "apixaban 5 mg BID"))
  query = f"MRN {mrn}: eGFR {gfr}, on {medication}. Dose-adjust or stop?"
  return UsabilityCase(
    id=case_id,
    category="renal_dosing",
    query=query,
    phi=(mrn,),
    critical_facts=(
      CriticalFact("kidney function", (f"eGFR {gfr}", f"GFR {gfr}")),
      CriticalFact("medication dose", (medication,)),
    ),
  )


def _case_pregnancy_med(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  first, last = _name(rng)
  weeks = rng.choice((10, 18, 28, 32, 36))
  med = rng.choice(("nitrofurantoin", "cephalexin", "ondansetron"))
  query = f"{first} {last}, {weeks} weeks pregnant, UTI symptoms. Is {med} safe?"
  return UsabilityCase(
    id=case_id,
    category="pregnancy_med",
    query=query,
    phi=(first, last),
    critical_facts=(
      CriticalFact("gestational age", (f"{weeks} weeks pregnant",)),
      CriticalFact("condition", ("UTI",)),
      CriticalFact("medication", (med,)),
    ),
  )


def _case_red_flag(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  child = rng.choice(FIRST_NAMES)
  relative = rng.choice(RELATIVES)
  query = (
    f"Mom ({relative}) says little {child} has fever for 5 days, red eyes, "
    "and rash. Could this be Kawasaki?"
  )
  return UsabilityCase(
    id=case_id,
    category="red_flag",
    query=query,
    phi=(relative, child),
    critical_facts=(
      CriticalFact("fever duration", ("5 days",)),
      CriticalFact("red eyes", ("red eyes",)),
      CriticalFact("rash", ("rash",)),
      CriticalFact("condition", ("Kawasaki",)),
    ),
  )


def _case_screening_guideline(
  rng: random.Random,
  reference_date: date,
  case_id: str,
) -> UsabilityCase:
  first, last = _name(rng)
  age = rng.choice((45, 50, 55, 64, 71))
  dob = _dob_for_age(age, reference_date, rng)
  practice = rng.choice(PRACTICES)
  query = (
    f"{first} {last}, DOB {dob}, seen today at {practice}. Colonoscopy overdue; "
    f"what does USPSTF say about screening at age {age}?"
  )
  return UsabilityCase(
    id=case_id,
    category="screening_guideline",
    query=query,
    phi=(first, last, dob, practice),
    critical_facts=(
      CriticalFact("age", (f"{age}-year-old", f"age {age}")),
      CriticalFact("screening topic", ("colonoscopy", "colorectal")),
      CriticalFact("guideline source", ("USPSTF",)),
    ),
  )


def _case_asthma_action(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  phone = _phone(rng)
  sat = rng.choice((91, 92, 93, 94))
  puffs = rng.choice((2, 4, 6))
  city = rng.choice(CITIES)
  state = rng.choice(STATES)
  query = (
    f"Family contact {phone} from {city}, {state}: asthma flare, O2 sat {sat}%, "
    f"using albuterol {puffs} puffs q4h, still wheezing. ER threshold?"
  )
  return UsabilityCase(
    id=case_id,
    category="asthma_action",
    query=query,
    phi=(phone, city, state),
    critical_facts=(
      CriticalFact("oxygen saturation", (f"O2 sat {sat}%", f"sat {sat}%")),
      CriticalFact("medication use", (f"albuterol {puffs} puffs",)),
      CriticalFact("symptom", ("wheezing",)),
      CriticalFact("triage intent", ("ER threshold",)),
    ),
  )


def _case_allergy_antibiotic(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  email = _email(rng)
  allergy = rng.choice(("amoxicillin allergy", "penicillin anaphylaxis", "sulfa rash"))
  diagnosis = rng.choice(("sinusitis", "AOM", "pneumonia"))
  query = f"Email {email}: {diagnosis} with {allergy}. Best antibiotic alternative?"
  return UsabilityCase(
    id=case_id,
    category="allergy_antibiotic",
    query=query,
    phi=(email,),
    critical_facts=(
      CriticalFact("diagnosis", (diagnosis,)),
      CriticalFact("allergy", (allergy,)),
      CriticalFact("intent", ("antibiotic alternative",)),
    ),
  )


def _case_no_phi_guideline(rng: random.Random, reference_date: date, case_id: str) -> UsabilityCase:
  query, facts = rng.choice((
    (
      "ACIP HPV vaccine schedule for 11-year-olds?",
      (CriticalFact("age", ("11-year-old", "11-year-olds")), CriticalFact("topic", ("HPV",))),
    ),
    (
      "First-line antibiotic for uncomplicated UTI in adult women?",
      (CriticalFact("condition", ("UTI",)), CriticalFact("population", ("adult women",))),
    ),
    (
      "When to refer for sleep study in suspected OSA?",
      (CriticalFact("condition", ("OSA",)), CriticalFact("intent", ("sleep study",))),
    ),
  ))
  return UsabilityCase(
    id=case_id,
    category="no_phi_guideline",
    query=query,
    phi=(),
    critical_facts=facts,
  )


def _case_dictation_buried_phi(
  rng: random.Random,
  reference_date: date,
  case_id: str,
) -> UsabilityCase:
  first, last = _name(rng)
  mrn = _mrn(rng)
  dob = _dob_for_age(rng.choice((4, 6, 8, 12)), reference_date, rng)
  query = (
    f"This is Dr. Hobbs dictating on patient number {mrn}, {first} {last}, "
    f"date of birth {dob}. Chief complaint is cafe-au-lait spots. "
    "Assessment is rule out NF1. Need current diagnostic criteria."
  )
  return UsabilityCase(
    id=case_id,
    category="dictation_buried_phi",
    query=query,
    phi=(mrn, first, last, dob, "Dr. Hobbs"),
    critical_facts=(
      CriticalFact("finding", ("cafe-au-lait spots",)),
      CriticalFact("condition", ("NF1",)),
      CriticalFact("intent", ("diagnostic criteria",)),
    ),
  )


def _name(rng: random.Random) -> tuple[str, str]:
  return rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)


def _dob_for_age(age: int, reference_date: date, rng: random.Random) -> str:
  month = rng.randint(1, 12)
  day = rng.randint(1, 28)
  year = reference_date.year - age
  if (month, day) > (reference_date.month, reference_date.day):
    year -= 1
  return f"{year:04d}-{month:02d}-{day:02d}"


def _mrn(rng: random.Random) -> str:
  return rng.choice((
    f"LP-{rng.randint(10000, 99999)}",
    f"AB{rng.randint(100000, 999999)}",
    f"HOSP-2024-{rng.randint(1000, 9999)}",
    str(rng.randint(1000000, 9999999)),
  ))


def _phone(rng: random.Random) -> str:
  return f"{rng.randint(200, 999)}-{rng.randint(200, 999)}-{rng.randint(1000, 9999)}"


def _email(rng: random.Random) -> str:
  first, last = _name(rng)
  return f"{first.lower()}.{last.lower().replace(' ', '').replace(chr(39), '')}@example.com"

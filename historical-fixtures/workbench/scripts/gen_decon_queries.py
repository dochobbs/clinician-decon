"""Synthesize a large PHI-decon test set from templates.

Produces ~500 queries with known PHI ground truth, diverse across:
  - Name types (US, foreign, hyphenated, with/without titles)
  - MRN formats (numeric, alphanumeric, hyphenated, prefixed)
  - Date formats (ISO, US, short, multi)
  - Phone formats (US, dotted, intl)
  - SSN with/without dashes, with/without keyword
  - Email
  - Address fragments
  - Demographic shorthand (must NOT be tagged)
  - Clinical-lookalike values (false-positive bait)
  - Dense multi-PHI strings
  - PHI-free baselines

Usage:
  python3 scripts/gen_decon_queries.py --n 500 --out data/decon_synth_500.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

# Realistic-but-synthetic PHI source data
FIRST_NAMES = ["Sarah", "John", "Maria", "Aisha", "Jiang", "Søren", "Robert",
               "Lisa", "Linda", "Marcus", "Emma", "James", "Patricia", "Mohammed",
               "Wei", "Carlos", "Yuki", "Olivia", "Amir", "Priya", "Daniel",
               "Eve", "Henry", "Isabella", "Liam", "Noah", "Mia", "Lucas",
               "Sophia", "Ethan", "Aria", "Mateo", "Charlotte", "Wei-Ming",
               "Jean-Pierre", "Mary-Ann", "Bo", "Rashida", "Tomás", "Yael"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
              "Miller", "Davis", "Martinez", "Park", "Wong", "Chen", "Singh",
              "Kim", "Patel", "O'Brien", "MacDonald", "Schwarz", "Andersson",
              "Mohammed", "van der Berg", "Anderson", "Thompson", "Taylor",
              "Wilson", "Thomas", "Hernandez", "Lopez", "Gonzalez"]
CITIES = ["Chicago", "Boston", "Seattle", "Atlanta", "Denver", "Phoenix",
          "Portland", "Minneapolis", "Tampa", "Austin", "San Diego",
          "Fairview", "Lakeville", "Riverside", "Springfield"]
STATES = ["IL", "MA", "WA", "GA", "CO", "AZ", "OR", "MN", "FL", "TX",
          "CA", "NY", "PA", "OH", "MI"]
STREETS = ["Park Lane", "Main St", "Oak Ave", "Maple Dr", "Elm St",
           "Cedar Ln", "Pine St", "Birch Rd", "Willow Way", "1st Avenue"]


def rand_dob_iso() -> str:
  y = random.randint(1930, 2025)
  m = random.randint(1, 12)
  d = random.randint(1, 28)
  return f"{y:04d}-{m:02d}-{d:02d}"


def rand_dob_us() -> str:
  y = random.randint(1930, 2025)
  m = random.randint(1, 12)
  d = random.randint(1, 28)
  return f"{m:02d}/{d:02d}/{y:04d}"


def rand_phone() -> str:
  area = random.randint(200, 999)
  exch = random.randint(200, 999)
  num = random.randint(1000, 9999)
  fmt = random.choice(["dash", "paren", "dot", "intl"])
  if fmt == "dash":     return f"{area}-{exch}-{num}"
  if fmt == "paren":    return f"({area}) {exch}-{num}"
  if fmt == "dot":      return f"{area}.{exch}.{num}"
  return f"+1 {area} {exch} {num}"


def rand_email() -> str:
  fn = random.choice(FIRST_NAMES).lower()
  ln = random.choice(LAST_NAMES).lower().replace("'", "").replace(" ", "")
  domain = random.choice(["example.com", "gmail.com", "hospital.org",
                          "clinic.io", "yahoo.com"])
  return f"{fn}.{ln}@{domain}"


def rand_ssn(dashes: bool = True) -> str:
  s = f"{random.randint(100,899):03d}{random.randint(10,99):02d}{random.randint(1000,9999):04d}"
  if dashes:
    return f"{s[:3]}-{s[3:5]}-{s[5:]}"
  return s


def rand_mrn() -> tuple[str, str]:
  fmt = random.choice(["numeric_short", "numeric_long", "alpha_dash",
                       "hosp_prefix", "ab_prefix", "mrn_keyword"])
  if fmt == "numeric_short":
    return f"MRN {random.randint(100000, 9999999)}", str(random.randint(100000, 9999999))
  if fmt == "numeric_long":
    n = random.randint(10**9, 10**10-1)
    return f"MRN {n}", str(n)
  if fmt == "alpha_dash":
    val = f"LP-{random.randint(10000, 99999)}"
    return f"MRN {val}", val
  if fmt == "hosp_prefix":
    val = f"HOSP-2024-{random.randint(1000, 9999)}"
    return f"MRN: {val}", val
  if fmt == "ab_prefix":
    val = f"{random.choice(['AB','XY','LP','RM'])}{random.randint(100000, 999999)}"
    return f"MR# {val}", val
  # mrn_keyword
  val = str(random.randint(1000000, 9999999))
  return f"Medical Record Number {val}", val


def rand_zip() -> str:
  return f"{random.randint(10000, 99999):05d}"


def fname_lname() -> tuple[str, str]:
  return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def rand_age() -> int:
  return random.randint(1, 95)


# ---- Templates ----

CLINICAL_QUESTIONS_W_NAME = [
  "{first} {last} has fever 102 for 3 days, workup?",
  "Pt {first} {last}, {age}M on lisinopril 20mg, BP 138/85, titrate?",
  "{first} {last} ({age}F) presents with chest pain, ECG normal — next?",
  "{first} {last} due for HPV vaccine, when do we start?",
  "{first} {last} has new dx HTN — first-line agent for African-American adult?",
  "Pt {first} {last}, {age}yo, breast lump 1.5cm, mammogram next?",
  "{first} {last} (3yo) has otitis media, abx?",
  "{first} {last}, peri-menopausal, hot flashes — HRT?",
  "Pt {first} {last} (newborn) has hyperbilirubinemia, phototherapy thresholds?",
  "{first} {last} on metformin, A1c 7.9 — second-line?",
]

CLINICAL_QUESTIONS_W_DOB = [
  "DOB {dob_iso}, fever 39 at 6 weeks — manage?",
  "Pt DOB {dob_iso} on warfarin, INR 1.8 — adjust?",
  "Pediatric pt DOB {dob_us}, vaccines due?",
  "{age}yo (DOB {dob_iso}) statin recommendation?",
]

CLINICAL_QUESTIONS_W_MRN = [
  "{mrn_str} on metformin, dose-adjust for CKD3?",
  "{mrn_str} has new dx HTN — first-line?",
  "Patient {mrn_str} needs prior auth for tirzepatide.",
  "{mrn_str}, BP 145/92, recheck interval?",
  "{mrn_str} due for screening colonoscopy — when?",
]

CLINICAL_QUESTIONS_W_PHONE = [
  "Pt phone {phone} for vaccine reminders, what protocol?",
  "Family contact {phone}, BP medication refill workflow?",
]

CLINICAL_QUESTIONS_W_EMAIL = [
  "Pt email {email} asks about cholesterol screening, what to recommend?",
  "Email {email} regarding annual physical scheduling, what to send?",
]

CLINICAL_QUESTIONS_W_SSN = [
  "Pt SSN {ssn_dash}, Medicare eligibility for screening colonoscopy?",
  "SSN {ssn_no_dash} on file, prior auth for tirzepatide?",
]

CLINICAL_QUESTIONS_W_ADDRESS = [
  "Pt at {street}, {city}, {state} {zip}, asks about flu shot?",
  "Lives on {street}, lead screening recommendation?",
  "Pt from {city}, {state} — TB screening required?",
]

CLINICAL_QUESTIONS_DENSE = [
  "{first} {last} (DOB {dob_iso}, MRN {mrn_val}, phone {phone}) needs HPV vaccine, when to start?",
  "{first} {last} DOB {dob_iso} SSN {ssn_dash} {email} — A1c 7.9 last month, next step?",
  "Family of {first} {last} (DOB {dob_iso}, MRN {mrn_val}, lives at {street}, {city}) wants advice on dad's CHF management.",
  "Patient {first} {last} (phone {phone}, email {email}, SSN {ssn_dash}) presents to clinic at {street}, {city}, {state} {zip} for annual visit. What's due?",
]

NO_PHI_QUESTIONS = [
  "What's the workup for iron deficiency anemia in adult women?",
  "When do we start statins per USPSTF?",
  "Tdap booster interval in adults?",
  "Recommended dose of amoxicillin for AOM in a 5yo?",
  "Diagnostic threshold for hypertension per ACC/AHA?",
  "USPSTF colorectal cancer screening recommendation?",
  "ACIP HPV vaccine schedule for 11-year-olds?",
  "First-line agent for newly diagnosed Type 2 DM?",
  "AAP recommendations for screen time in toddlers?",
  "How is anaphylaxis treated?",
  "What is the diagnostic criteria for sepsis in pediatrics?",
  "First-line agent for primary HTN per JNC 8?",
  "When to perform DEXA scan for osteoporosis screening?",
  "Empiric abx for adult outpatient CAP per ATS/IDSA?",
  "What's the GFR threshold to discontinue metformin?",
  "When do we start lipid-lowering therapy in adults?",
  "What's the recommended A1c target for most adults with DM?",
  "When to refer for sleep study in suspected OSA?",
  "First-line antibiotic for uncomplicated UTI in adult women?",
  "Vaccine schedule for healthy adult ages 50+?",
]

CLINICAL_LOOKALIKE_QUESTIONS = [
  "A1c {a1c} — next step in DM2 management?",
  "B12 {b12} in 70F with neuropathy, supplementation dose?",
  "TSH {tsh} with low T4, levothyroxine dosing?",
  "LDL {ldl} in 45M, statin first-line?",
  "ALT {alt} / AST {ast} — workup priorities?",
  "GFR {gfr}, age 72, dose-adjust metformin?",
  "Metformin {dose} mg BID, when to add second-line?",
  "Lisinopril {dose} mg, BP {bp_sys}/{bp_dia}, titrate up?",
  "ICD-10 E11.9 with HCC adjustment, A1c target?",
  "CPT 99213 visit, BP {bp_sys}/{bp_dia}, HTN management?",
  "Amoxicillin {dose} mg BID for adult sinusitis — duration?",
  "CMP normal except glucose {gluc} fasting, dx DM2?",
  "WBC {wbc}, fever 102 — workup?",
  "Hgb {hgb}, MCV 78 — iron deficiency or thalassemia?",
  "Platelet {plt}, no bleeding — workup?",
]


def gen_query(template: str, phi_extra: list[str] | None = None) -> tuple[str, list[str]]:
  """Fill template, return (query, list_of_phi_terms)."""
  fname, lname = fname_lname()
  age = rand_age()
  dob_iso = rand_dob_iso()
  dob_us = rand_dob_us()
  phone = rand_phone()
  email = rand_email()
  ssn_d = rand_ssn(dashes=True)
  ssn_nd = rand_ssn(dashes=False)
  mrn_str, mrn_val = rand_mrn()
  street = random.choice(STREETS)
  city = random.choice(CITIES)
  state = random.choice(STATES)
  zip_ = rand_zip()

  ctx = {
    "first": fname, "last": lname, "age": age,
    "dob_iso": dob_iso, "dob_us": dob_us,
    "phone": phone, "email": email,
    "ssn_dash": ssn_d, "ssn_no_dash": ssn_nd,
    "mrn_str": mrn_str, "mrn_val": mrn_val,
    "street": f"{random.randint(10, 9999)} {street}",
    "city": city, "state": state, "zip": zip_,
    "a1c": round(random.uniform(5.0, 12.0), 1),
    "b12": random.randint(100, 800),
    "tsh": round(random.uniform(0.1, 25.0), 1),
    "ldl": random.randint(60, 250),
    "alt": random.randint(20, 600),
    "ast": random.randint(20, 600),
    "gfr": random.randint(15, 90),
    "dose": random.choice([10, 20, 50, 250, 500, 850, 1000]),
    "bp_sys": random.randint(110, 180), "bp_dia": random.randint(60, 110),
    "gluc": random.randint(80, 250),
    "wbc": round(random.uniform(2.0, 20.0), 1),
    "hgb": round(random.uniform(7.0, 16.0), 1),
    "plt": random.randint(30, 500),
  }
  query = template.format(**ctx)

  # Determine PHI terms in this query
  phi = []
  if "{first}" in template:    phi.append(fname)
  if "{last}" in template:     phi.append(lname)
  if "{dob_iso}" in template:  phi.append(dob_iso)
  if "{dob_us}" in template:   phi.append(dob_us)
  if "{phone}" in template:    phi.append(phone)
  if "{email}" in template:    phi.append(email)
  if "{ssn_dash}" in template: phi.append(ssn_d)
  if "{ssn_no_dash}" in template: phi.append(ssn_nd)
  if "{mrn_str}" in template:  phi.append(mrn_val)  # underlying ID is the PHI
  if "{mrn_val}" in template:  phi.append(mrn_val)
  if "{street}" in template:   phi.append(street)
  if "{city}" in template:     phi.append(city)
  if "{zip}" in template:      phi.append(zip_)
  if phi_extra:
    phi.extend(phi_extra)

  return query, phi


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--n", type=int, default=500)
  ap.add_argument("--out", default="data/decon_synth_500.json")
  ap.add_argument("--seed", type=int, default=42)
  args = ap.parse_args()

  random.seed(args.seed)

  # Mix the categories — distribution roughly mirrors real-world frequency
  template_pools = [
    ("name", CLINICAL_QUESTIONS_W_NAME, 0.28),
    ("dob", CLINICAL_QUESTIONS_W_DOB, 0.10),
    ("mrn", CLINICAL_QUESTIONS_W_MRN, 0.12),
    ("phone", CLINICAL_QUESTIONS_W_PHONE, 0.04),
    ("email", CLINICAL_QUESTIONS_W_EMAIL, 0.04),
    ("ssn", CLINICAL_QUESTIONS_W_SSN, 0.04),
    ("address", CLINICAL_QUESTIONS_W_ADDRESS, 0.06),
    ("dense_multi_phi", CLINICAL_QUESTIONS_DENSE, 0.10),
    ("no_phi", NO_PHI_QUESTIONS, 0.12),
    ("clinical_lookalike", CLINICAL_LOOKALIKE_QUESTIONS, 0.10),
  ]
  weights = [w for _, _, w in template_pools]

  queries = []
  for i in range(args.n):
    cat, pool, _ = random.choices(template_pools, weights=weights, k=1)[0]
    template = random.choice(pool)
    if cat == "no_phi":
      query, phi = template, []
    else:
      query, phi = gen_query(template)
    queries.append({
      "id": f"S{i+1:04d}",
      "category": cat,
      "query": query,
      "phi": phi,
    })

  Path(args.out).parent.mkdir(parents=True, exist_ok=True)
  with open(args.out, "w") as fh:
    json.dump(queries, fh, indent=2)

  cat_count = {}
  for q in queries:
    cat_count[q["category"]] = cat_count.get(q["category"], 0) + 1
  total_phi = sum(len(q["phi"]) for q in queries)
  print(f"Generated {len(queries)} queries → {args.out}")
  print(f"  total PHI terms: {total_phi}")
  print(f"  category distribution:")
  for cat, n in sorted(cat_count.items(), key=lambda x: -x[1]):
    print(f"    {cat:25s}  {n:>3d}")


if __name__ == "__main__":
  main()

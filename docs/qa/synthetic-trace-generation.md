# Synthetic Trace Generation Strategy

Date: 2026-06-15

This document describes how Clinician Decon should generate high-quality synthetic traces for
rapid local validation without requiring thousands of clinician-authored gold cases.

## Goal

Generate many labeled traces that test two things at the same time:

1. PHI is removed or blocked before copy/open handoff.
2. Clinically necessary facts remain useful for the downstream LLM or search task.

The traces should be good enough to catch product regressions quickly and to support partner
conversations. They are not a replacement for clinician-reviewed gold validation.

## Core Approach

Use clinician-reviewed archetypes, then expand them synthetically.

The first shared persona library is versioned at
`package/data/personas/v1.json` and documented in `docs/qa/persona-library.md`.
Generators should combine clinician, patient/context, source-channel, and perturbation personas
from that file before filling archetype slots.

An archetype is a compact clinical scenario with explicit labels:

```json
{
  "id": "vaccine-catchup-buried-identity",
  "task": "vaccine catch-up",
  "template": "The patient I'm asking about is {patient_name}, D.O.B. {dob}, MRN {mrn}. Parent asks whether an under-immunized {age}-year-old needs {vaccine}.",
  "slots": {
    "patient_name": "phi.name",
    "dob": "phi.dob",
    "mrn": "phi.mrn",
    "age": "clinical.age",
    "vaccine": "clinical.vaccine"
  },
  "must_remove_phi": ["patient_name", "dob", "mrn"],
  "must_preserve_clinical_fact": ["age", "under-immunized", "vaccine"],
  "acceptable_generalization": {
    "dob": "clinical age band"
  },
  "unsafe_if_preserved": ["patient_name", "dob", "mrn"]
}
```

The generator expands the archetype by filling slots, applying perturbations, and writing
trace JSON with stable expected labels.

Persona IDs should be written into each generated trace so future failures can be traced back
to the exact clinician viewpoint, patient context, source channel, and perturbation profile.

## Why Archetypes Work

Pure random generation makes large numbers quickly but often creates low-value examples. Pure
clinician-authored gold sets are high quality but expensive.

Archetypes split the difference:

- a clinician reviews the clinical logic once
- the generator creates hundreds of variants
- labels remain deterministic because each generated value comes from a known slot
- failures can be traced back to a specific archetype and perturbation

## Trace Schema

Every generated case should include:

```json
{
  "id": "A0001",
  "source_archetype": "ocr-nf1-criteria",
  "category": "ocr_spaced_identifier",
  "query": "OCR export: M R N 8 2 9 3 4 1 5; D.O.B. 2017-04-10...",
  "phi": ["8 2 9 3 4 1 5", "2017-04-10", "Grace", "Walsh"],
  "forbidden_terms": [],
  "critical_facts": [
    {
      "label": "age",
      "acceptable_terms": ["school-age child"]
    },
    {
      "label": "condition",
      "acceptable_terms": ["NF1"]
    }
  ],
  "perturbations": ["ocr_spaced_mrn", "dotted_dob", "spaced_phone"],
  "seed": 20260615
}
```

Age labels should target the rendered safe form, not exact source age. Use clinical bands such as
`school-age child`, `adolescent`, or task-specific threshold hints such as
`early adolescent in HPV/Tdap vaccine range`.

Existing current suites already contain most of this shape:

- `query`
- `phi`
- `forbidden_terms`
- `critical_facts`

Next generator iteration should add:

- `source_archetype`
- `perturbations`
- `slot_values`
- `clinician_reviewed_archetype: true|false`

## Archetype Families

Minimum high-value families:

| Family | Why it matters |
| --- | --- |
| Canonical identifiers | Names, DOBs, MRNs, phone, email, SSN, URL, address. |
| Buried identity | Harmless lead-in followed by patient identity. |
| Dictation text | Physician dictation often includes names, DOBs, MRNs, and note sections. |
| OCR/copy artifacts | Spaced digits, dotted labels, broken punctuation, weird casing. |
| Multi-patient notes | Siblings, parent/child, twins, spouse, caregiver. |
| Spanish/family phrasing | Common non-English relationship forms and named relatives. |
| Small-town uniqueness | Rare disease plus practice, town, school, or local event. |
| Prompt injection | Text that tries to override PHI removal or force identifier disclosure. |
| Eponym collisions | Patient names that are also clinical terms, such as Hunter or Wilson. |
| Dosing precision | Weight, age, medication dose, renal function, pregnancy weeks. |
| Criteria precision | Severe labs, diagnostic criteria, red flags, vaccine catch-up. |
| Web-search compression | Cases where a search query must stay specific enough to be useful. |

## Perturbation Library

Each archetype can receive one or more perturbations:

- `case_noise`: uppercase, lowercase, title case, mixed casing
- `punctuation_noise`: missing periods, extra commas, semicolons, copied table text
- `ocr_spacing`: `M R N 1 2 3 4 5`, `5 1 2 5 5 5 0 1 4 7`
- `label_variants`: `DOB`, `D.O.B.`, `date of birth`, `born`
- `contact_obfuscation`: `john dot smith at example dot com`
- `url_embedding`: names/MRNs inside a path or query string
- `section_headers`: `SUBJECTIVE:`, `HPI:`, `ASSESSMENT:`, `CALLBACK:`
- `relationship_variants`: mom, mother, mama, abuela, brother, sibling, spouse
- `prompt_injection_variants`: system update, admin override, ignore previous instructions
- `clinical_lookalike`: exact values that look identifying but are clinically necessary

## Quality Rules

Generated traces should be rejected if:

- the clinical question is nonsensical
- the expected clinical facts are not present in the source text
- a generated PHI value is also required as a clinical fact without `forbidden_terms`
- the same generated case duplicates an existing ID/query pair
- a perturbation destroys the clinical intent

Generated suites should be deterministic:

- fixed seed
- fixed reference date
- stable row order
- stable IDs
- saved JSON checked into the repo for release gates

## Review Workflow

Practical clinician workload:

1. Create 100-150 archetypes.
2. Clinician reviews archetypes, not every generated row.
3. Generator expands to 1,000-5,000 cases.
4. Clinician spot-checks stratified output samples and all failure examples.
5. Validated archetypes become durable regression sources.

This gives high trace volume while keeping clinician time realistic.

## Dataset Split

Use three sets:

| Split | Purpose | Tuning allowed? |
| --- | --- | --- |
| `dev` | Find failures and improve rules/model behavior. | Yes |
| `regression` | Run on every commit and release. | Yes, but keep history of failures. |
| `frozen-validation` | Support external claims. | No direct tuning after failures are observed. |

The current `usability` and `adversarial` suites are regression gates. Future clinician-reviewed
archetype expansions should add a frozen validation split.

## Current Baseline

Current repo gates:

- `package/data/personas/v1.json`
- `package/data/archetypes/v1.json`
- `package/data/decon_usability_500_2026-06-15.json`
- `package/data/decon_adversarial_500_2026-06-15.json`
- `package/data/decon_persona_regression_2000_2026-06-15.json`

The default `current` gate provides:

- `1,000` labeled source cases
- `3,000` destination outputs across ChatGPT, Gemini, and Web Search
- `0` detected PHI leaks in the current run
- `0` missing required clinical facts in the current run

Run them with:

```bash
python3 package/scripts/run_validation.py --suite current
```

The persona-driven regression gate provides:

- `2,000` labeled source cases
- `6,000` destination outputs across ChatGPT, Gemini, and Web Search
- `0` detected PHI leaks in the final current run
- `0` missing required clinical facts in the final current run

Run it with:

```bash
python3 package/scripts/run_validation.py --suite persona-regression
```

## Implemented Generator

The first archetype generator writes versioned datasets:

```bash
python3 package/scripts/generate_traces.py \
  --personas package/data/personas/v1.json \
  --archetypes package/data/archetypes/v1.json \
  --count 2000 \
  --seed 20260615 \
  --output package/data/decon_persona_regression_2000_2026-06-15.json \
  --report package/reports/persona-regression-2000-2026-06-15.json
```

The generated output should then run through the same headless validation command.

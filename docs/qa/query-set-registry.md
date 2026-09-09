# Decon Query Set Registry

Date: 2026-06-15

This registry traces the decontextualization query sets in this repo: where they came from,
what they are meant to test, how to reproduce generated sets, and which QA summary currently
records the latest local result.

Related docs:

- `docs/qa/2026-09-09-hybrid-decon-hardening-handoff.md`: current canonical closeout for the
  OpenMed-plus-rules hybrid, PPLX comparison, release gates, and remaining evidence boundary.
- `docs/qa/2026-06-19-project-pickup-handoff.md`: historical project state, cleanup, validation
  status, and next steps before the September hybrid hardening.
- `docs/qa/headless-validation.md`: how to run the validation gate from a clone or CI.
- `docs/qa/synthetic-trace-generation.md`: how to generate higher-quality synthetic traces from
  clinician-reviewed archetypes.
- `docs/qa/persona-library.md`: the versioned persona vocabulary used by the persona-driven
  generator.
- `docs/qa/2026-06-15-persona-regression-2000-eval.md`: first 2,000-case persona-regression
  run, failure trace, fixes, and final result.
- `docs/qa/2026-06-16-local-rules-openmed-audit.md`: model-backed pipeline audit and
  seed-gold verification.
- `docs/qa/2026-06-16-external-deid-adversarial-addon-head-to-head.md`: 50-case add-on built to test
  patterns where a broad external de-ID baseline might plausibly be competitive.
- `docs/qa/2026-06-19-realworld-adversarial-hardening.md`: real-world copied-note,
  EHR-wrapper, HL7, relative-date, and clinical-usability hardening trace.
- `docs/qa/2026-09-02-pplx-pii-masking-openmed-head-to-head.md`: full release-corpus and
  cross-turn comparison of the current OpenMed mode with the experimental PPLX adapter.
- `docs/qa/2026-09-02-residual-identifier-redteam.md`: evaluator correction and product-level
  coverage for partially masked and fragmented identifiers.

## Current Regression Gates

The default `current` gate runs the 500-case usability suite, the 500-case adversarial suite, and
the 50-case external de-ID adversarial add-on. Production validation should run it with
`--engine rules+openmed`, not rules-only `auto`. `clinician-seed-gold` is the high-signal 10-case
clinician review seed. `persona-regression` is a larger explicit gate that uses the versioned
persona and archetype libraries.

| Query set | Rows | Source | Purpose | Latest result |
| --- | ---: | --- | --- | --- |
| `package/data/decon_usability_500_2026-06-15.json` | 500 | `generate_usability_cases(500, seed=20260615, reference_date=2026-06-15)` in `package/src/decon/usability_eval.py` | Clinician-usability suite: checks whether decon preserves required clinical facts while removing PHI. | `docs/qa/2026-06-15-local-usability-500-eval.md`: 1,500 / 1,500 safe, clinically usable, and handoff usable. |
| `package/data/decon_adversarial_500_2026-06-15.json` | 500 | `generate_adversarial_cases(500, seed=20260615, reference_date=2026-06-15)` in `package/src/decon/usability_eval.py` | Adversarial stress suite for common failure modes: prompt injection, buried identity, repeated names, OCR identifiers, URL PHI, Spanish family phrasing, small-town uniqueness, copy-pasted notes, contact/date mashups, and eponym collisions. | `docs/qa/2026-06-15-local-adversarial-500-eval.md`: 1,500 / 1,500 safe, clinically usable, and handoff usable. |
| `package/data/decon_phi_field_prose_25_2026-06-15.json` | 25 | Clinician-authored focused audit from the Marvin-name failure follow-up. | Focused prose PHI field suite: month-name DOB, birthday, weekdays, spaced phones, obfuscated email, named pharmacy/school/camp, practice/location, insurance, and caregiver-name bridge. | `docs/qa/2026-06-15-other-phi-fields-prose-audit.md`: 75 / 75 safe, clinically usable, and handoff usable. |
| `package/data/decon_validation_blindspot_redteam_17_2026-06-15.json` | 17 | Skeptical validation audit after aggregate gates missed the Marvin live-server leak. | Hardens against evaluator blind spots: caregiver prose verbs, preferred-name labels, `Patient named`, dotted/no-comma/day-month DOBs, policy/license/IP identifiers, and apartment units. | `docs/qa/2026-06-15-validation-blindspot-red-team.md`: first run found 38 / 51 PHI-leaked outputs and 12 / 51 missing-critical-fact outputs; final run 51 / 51 safe, clinically usable, and handoff usable. |
| `package/data/decon_validation_blindspot_redteam_r2_25_2026-06-15.json` | 25 | Second skeptical clinician-authored pass after R1 fixes. | Hardens against more natural prose: `says that`, `per mom`, name-is/goes-by/alias labels, lowercase name labels, MOC/FOC, space/ISO/period DOBs, `MR #`, chart IDs with spaces, room numbers, hash unit numbers, and word-spelled phone numbers. | `docs/qa/2026-06-15-validation-blindspot-red-team-r2.md`: first run found 56 / 75 PHI-leaked outputs and 12 / 75 missing-critical-fact outputs; final run 75 / 75 safe, clinically usable, and handoff usable. |
| `package/data/decon_clinician_seed_gold_10_2026-06-16.json` | 10 | Clinician-selected hard cases created after the Marvin miss and OpenMed audit. | Seed-gold gate for patient-name prose, multi-patient sibling notes, legal-name labels, Spanish family phrasing, camp/school/pharmacy/location, and clinical eponym preservation. | `docs/qa/2026-06-16-local-rules-openmed-audit.md`: `rules+openmed` run on 2026-06-16 passed 30 / 30 outputs with 0 PHI leaks and 0 missing clinical facts. |
| `package/data/decon_external_deid_adversarial_addon_50_2026-06-16.json` | 50 | Hand-authored external de-ID adversarial add-on created from the external baseline comparison and local pipeline gaps. | Tests identifiers and formats where a broad de-ID tool might be competitive: accession, specimen, voiceprint, passport, license, military, claim, group, UUID, device IDs, HL7, FHIR, JSON, filenames, QR payloads, portal tokens, chat-export handles, Unicode, Spanish prose, facility locations, bus routes, and eponym/name-drug collisions. | `docs/qa/2026-06-16-external-deid-adversarial-addon-head-to-head.md`: Clinician Decon passed 150 / 150 outputs; the external baseline scored 31 / 50 safe and 35 / 50 clinically usable. |
| `package/data/decon_realworld_adversarial_24_2026-06-19.json` | 24 | Hand-authored real-world adversarial set created from manually reviewed copied EHR notes, portal snippets, and report/message formats. | Tests EHR wrapper labels, section-label names, PT false positives, exact clinical values, HL7, JSON, spoken contact info, location/practice/school context, prompt injection, and no-PHI controls. | `docs/qa/2026-06-19-realworld-adversarial-hardening.md`: initial run found EHR-wrapper noise, HL7 usability loss, and `tomorrow` specificity; final model-backed run passed 72 / 72 outputs with 0 PHI leaks and 0 missing clinical facts. |
| `package/data/decon_persona_regression_2000_2026-06-15.json` | 2,000 | `package/scripts/generate_traces.py --count 2000 --seed 20260615` using `package/data/personas/v1.json` and `package/data/archetypes/v1.json` | Persona-driven regression suite: combines clinician persona, patient context, source channel, perturbation, and clinical archetype metadata. | `docs/qa/2026-06-15-persona-regression-2000-eval.md`: first run found 2,742 / 6,000 PHI-leaked outputs; final run 6,000 / 6,000 safe, clinically usable, and handoff usable. |
| `generate_cross_turn_cases()` in `package/src/decon/conversation_eval.py` | 260 | Deterministic generator with 20 synthetic identities across 13 dialogue shapes. | Release gate with 180 repeated-PII dialogues, including long and multilingual cases, plus 80 PII-free clinical controls. | Initial comparison: OpenMed produced 750 / 780 handoff-usable outputs and PPLX 537 / 780. After name/handle propagation hardening, `rules+openmed` passed 780 / 780 with zero leaks and zero fact loss. |
| `package/data/decon_residual_identifier_redteam_12_2026-09-02.json` | 12 | Hand-authored synthetic add-on created after the final-output validator allowed `[MRN]DEFGHIJK`. | Release gate for partial and fragmented identifiers across unlabeled records, FHIR, HL7, JSON, OCR spacing, filenames, repeated values, multiple IDs, accounts, and portal tokens while checking clinical preservation. | `docs/qa/2026-09-02-residual-identifier-redteam.md`: initial OpenMed-backed run leaked 17 / 36 outputs; after structured-span and residual hardening it passed 36 / 36. PPLX also passed this narrow suite before the fix. |
| `generate_structured_boundary_cases()` in `package/src/decon/structured_boundary_eval.py` | 144 | Deterministic generator with 12 identifier families, eight hostile shapes per identifier, and four matched clean clinical controls per bundle. | Release gate for structured-field completeness and partial remnants while preventing success through indiscriminate over-redaction. | 2026-09-02 `rules+openmed` run passed 432 / 432 outputs with zero leaks, zero missing facts, and 100% handoff usability. Raw OpenMed alone leaked expected PHI in 61 / 144 source cases. |

## 2026-06-19 Regression Plus Real-World Gate

Validation:

```bash
DECON_HOME="$PWD/build/live-decon-home" \
DECON_MODEL_DIR="$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/package/local-models/<local-model-dir>" \
PYTHONPATH="$PWD/package/src:$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python-packages" \
"$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python/bin/python" \
  -m decon.validation_cli \
  --suite current \
  --suite phi-field-prose \
  --suite validation-blindspot-redteam \
  --suite validation-blindspot-redteam-r2 \
  --suite clinician-seed-gold \
  --suite realworld-adversarial \
  --destinations <configured-destinations> \
  --reference-date 2026-06-19 \
  --engine <model-backed-engine> \
  --report /private/tmp/regression-plus-realworld-2026-06-19-model.json
```

Result:

- Source cases: `1,151`
- Destination outputs: `3,453`
- PHI-leaked outputs: `0 / 3,453`
- Unsafe copy-allowed leaks: `0 / 3,453`
- Missing-critical-fact outputs: `0 / 3,453`
- Clinically usable outputs: `3,453 / 3,453`
- Handoff usable outputs: `3,453 / 3,453`
- Max average runtime: `306.361 ms`
- Max p95 runtime: `651.176 ms`

## 2026-06-16 OpenMed-Backed Current Gate

Validation:

```bash
PYTHONPATH=package/src /path/to/python-with-transformers \
  package/scripts/run_validation.py --engine rules+openmed
```

Result on the repo-local OpenMed model:

- Source cases: `1,050`
- Destination outputs: `3,150`
- PHI-leaked outputs: `0 / 3,150`
- Unsafe copy-allowed leaks: `0 / 3,150`
- Clinically usable outputs: `3,150 / 3,150`
- Missing-critical-fact outputs: `0 / 3,150`
- Clinical usability rate: `100.00%`
- Handoff usability rate: `100.00%`
- Max average runtime: `100.098 ms`
- Max p95 runtime: `123.279 ms`

The model was loaded from:

```text
package/local-models/OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1/
```

That directory is ignored by git and should be populated by the installer or local setup before
running `--engine rules+openmed`.

## Clinician Seed-Gold 10 Trace

Validation:

```bash
python3 package/scripts/run_validation.py --suite clinician-seed-gold --engine rules+openmed
```

Seed and date:

- Seed: none; clinician-selected deterministic cases.
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `10 cases x 3 destinations = 30 outputs`

Coverage:

- Marvin-style patient-name prose with caregiver, DOB, phone, camp, and medication side effects.
- Multi-patient sibling notes where both sibling names must be removed but both ages/facts remain.
- Clinical eponyms and patient names in the same note, especially `Addison disease`.
- Named pharmacy, location, school, camp, room, Spanish family phrasing, and legal-name labels.
- Rare-disease/search prompts where school/practice uniqueness must be removed but the clinical
  condition remains useful.

Current `rules+openmed` result:

- Safe outputs: `30 / 30`
- Clinically usable outputs: `30 / 30`
- Handoff usable outputs: `30 / 30`
- PHI-leaked outputs: `0 / 30`
- Missing-critical-fact outputs: `0 / 30`
- Max average runtime: `186.146 ms`
- Max p95 runtime: `106.107 ms`

## Persona Regression 2,000 Trace

Generator:

```bash
python3 package/scripts/generate_traces.py \
  --count 2000 \
  --seed 20260615 \
  --output package/data/decon_persona_regression_2000_2026-06-15.json \
  --report package/reports/persona-regression-2000-2026-06-15.json
```

Validation:

```bash
python3 package/scripts/run_validation.py --suite persona-regression
```

Seed and date:

- Seed: `20260615`
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `2,000 cases x 3 destinations = 6,000 outputs`

Coverage:

- `10` archetypes, exactly `200` cases each.
- `8` source-channel personas.
- `8` perturbation profiles.
- `2,000 / 2,000` cases include expected PHI and required clinical facts.

The first run found true local-rule misses:

- JSON chart fragments preserving `"patient_name":"Full Name"`.
- Phone notes preserving `caller <Name> at <PHONE>`.
- Relationship-noise prompts preserving `sibling <Name> is worried`.
- OCR-spaced alphanumeric MRNs such as `M R N L P 2 0 2 5 4 0 0 0 0`.

Final run after targeted fixes:

- Safe outputs: `6,000 / 6,000`
- Clinically usable outputs: `6,000 / 6,000`
- Handoff usable outputs: `6,000 / 6,000`
- PHI-leaked outputs: `0 / 6,000`
- Missing-critical-fact outputs: `0 / 6,000`
- Average runtime: `0.289 ms`
- p95 runtime: `0.399 ms`

## PHI Field Prose 25 Trace

Validation:

```bash
python3 package/scripts/run_validation.py --suite phi-field-prose
```

Seed and date:

- Seed: none; clinician-authored deterministic cases.
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `25 cases x 3 destinations = 75 outputs`

Coverage:

- Month-name DOB prose, including `date of birth`, `born`, and `birthday`.
- Relative weekdays and exact month-day dates.
- Standard and spaced phone numbers.
- Standard and obfuscated emails.
- SSN, URL, address, city/state, ZIP, MRN, and OCR-spaced MRN prose.
- Named pharmacy, school, camp, practice/location, and insurance references.
- Caregiver-name bridge: `Mother Jennifer reports Marvin...`.

Final run after fixes:

- Safe outputs: `75 / 75`
- Clinically usable outputs: `75 / 75`
- Handoff usable outputs: `75 / 75`
- PHI-leaked outputs: `0 / 75`
- Missing-critical-fact outputs: `0 / 75`

## Validation Blind-Spot Red-Team 17 Trace

Validation:

```bash
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam
```

Seed and date:

- Seed: none; skeptical clinician-authored cases.
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `17 cases x 3 destinations = 51 outputs`

Coverage:

- Caregiver prose verbs: `Mom says`, `Mother notes`, `Dad states`, and `Caller Jennifer says`.
- Name-label prose: `Preferred name:`, `Name:`, and `Patient named`.
- DOB formats the earlier gates under-sampled: dotted numeric, month-day-year without comma,
  and day-month-year.
- Identifier classes from the HIPAA-style remaining-gap list: policy IDs, driver license
  numbers, IP addresses, and apartment/unit fragments.

First run against the pre-fix rules:

- Safe outputs: `13 / 51`
- PHI-leaked outputs: `38 / 51`
- Missing-critical-fact outputs: `12 / 51`
- Clinically usable outputs: `39 / 51`
- Handoff usable outputs: `9 / 51`

Final run after fixes:

- Safe outputs: `51 / 51`
- Clinically usable outputs: `51 / 51`
- Handoff usable outputs: `51 / 51`
- PHI-leaked outputs: `0 / 51`
- Missing-critical-fact outputs: `0 / 51`

## Validation Blind-Spot Red-Team R2 25 Trace

Validation:

```bash
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam-r2
```

Seed and date:

- Seed: none; skeptical clinician-authored cases.
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `25 cases x 3 destinations = 75 outputs`

Coverage:

- Caregiver prose with `that` and `per caregiver` phrasing.
- `Child's name is`, `Patient goes by`, `Alias`, lowercase `patient name`, and lowercase
  `preferred name` labels.
- `MOC` and `FOC` parent abbreviations.
- DOB formats with spaces, ISO slashes, and abbreviated month periods.
- `MR #`, chart IDs with internal spaces, room numbers, hash unit numbers, and word-spelled
  phone numbers.

First run against the pre-fix rules:

- Safe outputs: `19 / 75`
- PHI-leaked outputs: `56 / 75`
- Missing-critical-fact outputs: `12 / 75`
- Clinically usable outputs: `63 / 75`
- Handoff usable outputs: `13 / 75`

Final run after fixes:

- Safe outputs: `75 / 75`
- Clinically usable outputs: `75 / 75`
- Handoff usable outputs: `75 / 75`
- PHI-leaked outputs: `0 / 75`
- Missing-critical-fact outputs: `0 / 75`

## Adversarial 500 Trace

Generator:

```bash
python3 package/scripts/run_adversarial_eval.py
```

Seed and date:

- Seed: `20260615`
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `500 cases x 3 destinations = 1,500 outputs`

Category distribution:

| Category | Cases | What it probes |
| --- | ---: | --- |
| `ocr_spaced_identifier` | 66 | Spaced MRNs, spaced callback numbers, dotted DOB labels, and age derivation. |
| `eponym_collision` | 60 | Patient-name collision with clinical eponyms such as `Hunter syndrome`. |
| `date_contact_mashup` | 51 | Spaced phone numbers, obfuscated emails, dates, and names in copied contact blocks. |
| `prompt_injection_override` | 51 | System/admin override text that tries to disable PHI removal. |
| `multi_patient_repeat` | 50 | Sibling names repeated later in a question and multiple clinically relevant ages. |
| `buried_patient_identity` | 47 | Identity hidden after harmless setup language such as `routine vaccine question`. |
| `small_town_unique` | 45 | Rare-condition plus practice/town uniqueness. |
| `spanish_family` | 44 | Spanish parent phrasing and named relatives. |
| `url_path_phi` | 44 | Chart URLs carrying patient names, MRNs, and callback values. |
| `copy_pasted_note` | 42 | SOAP-like note headers, age/sex compaction, thyroid labs, and symptoms. |

First run against the pre-fix local rules was intentionally bad:

- Safe outputs: `535 / 1,500`
- Clinically usable outputs: `1,205 / 1,500`
- PHI-leaked outputs: `965 / 1,500`
- Missing-critical-fact outputs: `295 / 1,500`

That run drove targeted fixes for:

- OCR-spaced MRNs and callback numbers.
- `D.O.B.` age derivation.
- Broad `SYSTEM UPDATE` / administrator override prompt-injection text.
- Names buried in `the patient I'm asking about is ...`.
- Names repeated later in sibling questions.
- Spanish full-name and named-relative phrasing.
- Small-town context after `in Town:`.
- Obfuscated emails with spaces, hyphens, apostrophes, and Latin-extended characters.
- Richer web-search queries for catch-up vaccine and sibling prompts.

Final run after fixes:

- Safe outputs: `1,500 / 1,500`
- Clinically usable outputs: `1,500 / 1,500`
- Handoff usable outputs: `1,500 / 1,500`
- PHI-leaked outputs: `0 / 1,500`
- Missing-critical-fact outputs: `0 / 1,500`
- Average runtime: `0.234 ms`
- p95 runtime: `0.315 ms`

## Usability 500 Trace

Generator:

```bash
python3 package/scripts/run_usability_eval.py
```

Seed and date:

- Seed: `20260615`
- Reference date: `2026-06-15`
- Destinations: default LLM and search destinations
- Outputs per run: `500 cases x 3 destinations = 1,500 outputs`

This suite asks whether clinically important facts survive decontextualization. The generated
families cover pediatric weight-based dosing, epinephrine dosing, severe lab criteria, vaccine
schedules, medication titration, renal dosing, pregnancy medication questions, red-flag triage,
screening guidance, asthma action questions, allergy/antibiotic alternatives, no-PHI guideline
queries, and dictation-style buried PHI.

The first run found a quality failure, not just safety failures: exact dosing weights and exact
HLH-style lab values were being over-generalized. The final run after targeted local-rule fixes:

- Safe outputs: `1,500 / 1,500`
- Clinically usable outputs: `1,500 / 1,500`
- Handoff usable outputs: `1,500 / 1,500`
- PHI-leaked outputs: `0 / 1,500`
- Missing-critical-fact outputs: `0 / 1,500`
- Average runtime: `0.153 ms`
- p95 runtime: `0.219 ms`

## Legacy Copied Sets

These sets were copied from prior decontextualization work and should remain available as
regression and research artifacts.

| Query set | Rows | Origin | Purpose |
| --- | ---: | --- | --- |
| `historical-fixtures/workbench/data/decon_synth_500.json` | 500 | Historical synthetic generator output | Broad synthetic PHI coverage across names, MRNs, dates, phones, addresses, SSNs, no-PHI guideline queries, dense PHI, and clinical lookalikes. |
| `historical-fixtures/workbench/data/decon_synth_500_b.json` | 500 | Historical synthetic generator output | Second broad synthetic 500-case draw for distribution diversity. |
| `historical-fixtures/workbench/data/decon_legacy_stress.json` | 132 | Historical decon stress cases | More adversarial prompt styles from earlier rounds, including name-in-query and other PHI stress categories. |
| `historical-fixtures/workbench/data/decon_combined_1132.json` | 1,132 | Combined historical synthetic plus stress corpus | Larger local-rules batch red-team corpus. See `docs/qa/2026-06-15-local-rules-1132-batch-red-team.md`. |
| `package/data/phi_stress_test*.json` | varies | Copied historical project/package fixtures | Historical PHI stress fixtures preserved for continuity with the original package. |

## Adding a New Query Set

For each new generated or clinician-authored set:

1. Save the case JSON under `package/data/` or the appropriate copied-source folder.
2. Include stable IDs, a category, the source query, expected PHI, and required critical facts.
3. Record generator function, seed, reference date, and row count in this registry.
4. Run the appropriate eval script and save a machine-readable report under `package/reports/` or
   `/private/tmp`; JSON reports are generated artifacts and are ignored by git.
5. Save a reader-facing report under `docs/qa/`.
6. Keep first-run failure summaries when they drove code changes.

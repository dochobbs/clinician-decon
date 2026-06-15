# Decon Query Set Registry

Date: 2026-06-15

This registry traces the decontextualization query sets in this repo: where they came from,
what they are meant to test, how to reproduce generated sets, and which report currently
records the latest local result.

## Current Regression Gates

| Query set | Rows | Source | Purpose | Latest result |
| --- | ---: | --- | --- | --- |
| `package/data/decon_usability_500_2026-06-15.json` | 500 | `generate_usability_cases(500, seed=20260615, reference_date=2026-06-15)` in `package/src/decon/usability_eval.py` | Clinician-usability suite: checks whether decon preserves required clinical facts while removing PHI. | `docs/qa/2026-06-15-local-usability-500-eval.md`: 1,500 / 1,500 safe, clinically usable, and handoff usable. |
| `package/data/decon_adversarial_500_2026-06-15.json` | 500 | `generate_adversarial_cases(500, seed=20260615, reference_date=2026-06-15)` in `package/src/decon/usability_eval.py` | Adversarial stress suite for common failure modes: prompt injection, buried identity, repeated names, OCR identifiers, URL PHI, Spanish family phrasing, small-town uniqueness, copy-pasted notes, contact/date mashups, and eponym collisions. | `docs/qa/2026-06-15-local-adversarial-500-eval.md`: 1,500 / 1,500 safe, clinically usable, and handoff usable. |

## Adversarial 500 Trace

Generator:

```bash
python3 package/scripts/run_adversarial_eval.py
```

Seed and date:

- Seed: `20260615`
- Reference date: `2026-06-15`
- Destinations: `chatgpt`, `gemini`, `web_search`
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
- Destinations: `chatgpt`, `gemini`, `web_search`
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
| `from-cds-eval/data/decon_synth_500.json` | 500 | `cds-eval` synthetic generator output | Broad synthetic PHI coverage across names, MRNs, dates, phones, addresses, SSNs, no-PHI guideline queries, dense PHI, and clinical lookalikes. |
| `from-cds-eval/data/decon_synth_500_b.json` | 500 | `cds-eval` synthetic generator output | Second broad synthetic 500-case draw for distribution diversity. |
| `from-cds-eval/data/decon_amboss_stress.json` | 132 | Amboss-derived decon stress cases | More adversarial prompt styles from earlier rounds, including name-in-query and other PHI stress categories. |
| `from-cds-eval/data/decon_combined_1132.json` | 1,132 | Combined `cds-eval` synthetic plus Amboss stress corpus | Larger local-rules batch red-team corpus. See `docs/qa/2026-06-15-local-rules-1132-batch-red-team.md`. |
| `package/data/phi_stress_test*.json` | varies | Copied Amboss/package fixtures | Historical PHI stress fixtures preserved for continuity with the original package. |

## Adding a New Query Set

For each new generated or clinician-authored set:

1. Save the case JSON under `package/data/` or the appropriate copied-source folder.
2. Include stable IDs, a category, the source query, expected PHI, and required critical facts.
3. Record generator function, seed, reference date, and row count in this registry.
4. Run the appropriate eval script and save a machine-readable report under `package/reports/`.
5. Save a reader-facing report under `docs/qa/`.
6. Keep first-run failure summaries when they drove code changes.

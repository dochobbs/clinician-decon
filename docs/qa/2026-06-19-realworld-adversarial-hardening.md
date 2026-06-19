# Real-World Adversarial Hardening

Date: 2026-06-19

Scope: `rules+openmed` decontextualization using the bundled local OpenMed model plus
deterministic regex/post-processing rules.

Primary suite:

- `package/data/decon_realworld_adversarial_24_2026-06-19.json`

Primary report:

- `package/reports/realworld-adversarial-24-2026-06-19-openmed.json`

Expanded regression report:

- `package/reports/regression-plus-realworld-2026-06-19-openmed.json`

## Why This Suite Exists

Manual review of real-looking decon outputs found failure modes that broad synthetic suites did not
make obvious enough:

- EHR export wrappers could survive in the prompt and make the output hard to read.
- Relative dates such as `tomorrow` were still too specific for the strict handoff policy.
- Pipe-delimited HL7-style messages were deidentified but remained too raw to be clinically usable.
- Clinical abbreviations, eponyms, section labels, and multi-patient notes needed to preserve facts
  without preserving names.

The goal of this suite is not to create isolated one-off patches. Each case represents a family of
clinician inputs that should generalize to future notes, portal messages, copied EHR snippets, and
lab/report exports.

## Query Families

| Family | Cases | What It Tests |
| --- | ---: | --- |
| EHR/export wrappers | 2 | Header labels, note-body labels, DOB-to-age, sex preservation, section-label names |
| Clinical parentheticals | 2 | Drug/vaccine abbreviations vs parenthetical patient names |
| Contact and identifier variants | 5 | URLs, spoken phone/email, JSON fields, MRN formats, insurance fields |
| Clinical value preservation | 5 | Weight-based dosing, severe labs, A1c/BMI generalization, renal dosing |
| Name/eponym collisions | 3 | Addison disease, Hunter syndrome, legal/preferred names |
| Location/practice/school context | 4 | Address, ZIP/location, school, bus route, practice/facility identifiers |
| Safety and prompt attack | 2 | Suicidal ideation context, prompt injection asking to preserve PHI |
| No-PHI control | 1 | Ensures useful clinical text is not mangled when no identifiers are present |

## Initial Findings

The first model-backed run found real gaps:

| Issue | Outputs Affected | General Problem |
| --- | ---: | --- |
| EHR wrapper noise | 6 | `ELATION NOTE`, `Patient:`, `MRN:`, `Serviced at:`, and `Sex:` survived |
| Missing critical facts | 3 | HL7 output did not express `female` or `elevated TSH` in readable form |
| Relative date specificity | 3 | `tomorrow` survived in a copied prompt |

These were fixed as rule families, not literal case exceptions.

## Changes Made

Generalized engine changes:

- Added relative-date handling for `tomorrow`, rendered as `next day`.
- Added EHR wrapper cleanup for common exported-note labels and deidentified header fields.
- Preserved broad sex context by converting `Sex: Male/Female` to `male` or `female`.
- Added HL7-style pipe message normalization:
  - removes raw transport/admin segments from copied output;
  - preserves PID sex as broad clinical context;
  - summarizes OBX lab values using the existing clinical-value generalizer;
  - keeps non-HL7 clinical question text.

Regression tests added:

- EHR wrapper cleanup preserves age, sex, vaccines, medication, and side-effect context.
- HL7 normalization removes identifiers and preserves `female patient`, `elevated TSH`, and the
  clinical question.
- Legal/preferred-name psych safety test now requires `tomorrow` to become `next day`.

## Validation Commands

Focused rules test:

```bash
python3 -m pytest package/tests/test_local_rules.py -q
```

Focused model-backed adversarial suite:

```bash
DECON_HOME="$PWD/build/live-decon-home" \
DECON_MODEL_DIR="$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/package/local-models/OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1" \
PYTHONPATH="$PWD/package/src:$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python-packages" \
"$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python/bin/python" \
  -m decon.validation_cli \
  --suite realworld-adversarial \
  --destinations chatgpt,gemini,web_search \
  --reference-date 2026-06-19 \
  --engine rules+openmed \
  --report package/reports/realworld-adversarial-24-2026-06-19-openmed.json
```

Expanded model-backed regression:

```bash
DECON_HOME="$PWD/build/live-decon-home" \
DECON_MODEL_DIR="$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/package/local-models/OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1" \
PYTHONPATH="$PWD/package/src:$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python-packages" \
"$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python/bin/python" \
  -m decon.validation_cli \
  --suite current \
  --suite phi-field-prose \
  --suite validation-blindspot-redteam \
  --suite validation-blindspot-redteam-r2 \
  --suite clinician-seed-gold \
  --suite realworld-adversarial \
  --destinations chatgpt,gemini,web_search \
  --reference-date 2026-06-19 \
  --engine rules+openmed \
  --report package/reports/regression-plus-realworld-2026-06-19-openmed.json
```

Full package test:

```bash
python3 -m pytest package/tests -q
```

## Results After Hardening

Focused real-world adversarial suite:

| Metric | Result |
| --- | ---: |
| Source cases | 24 |
| Outputs | 72 |
| PHI leaked outputs | 0 |
| Unsafe copy-allowed leaks | 0 |
| Missing critical fact outputs | 0 |
| Clinical usability rate | 100.00% |
| Handoff usability rate | 100.00% |
| Max avg runtime | 129.788 ms |
| Max p95 runtime | 125.989 ms |

Expanded regression plus real-world suite:

| Metric | Result |
| --- | ---: |
| Source cases | 1,151 |
| Outputs | 3,453 |
| PHI leaked outputs | 0 |
| Unsafe copy-allowed leaks | 0 |
| Missing critical fact outputs | 0 |
| Clinical usability rate | 100.00% |
| Handoff usability rate | 100.00% |
| Max avg runtime | 94.573 ms |
| Max p95 runtime | 114.391 ms |

Package tests:

| Command | Result |
| --- | --- |
| `python3 -m pytest package/tests/test_local_rules.py -q` | 74 passed |
| `python3 -m pytest package/tests -q` | 147 passed |

## Remaining Caution

This is still synthetic and labeled validation. It is useful for regression hardening, but it does
not replace clinician review of real-world examples. The model-backed path must continue to fail
closed when OpenMed is requested but unavailable, and release claims should stay scoped to the
tested `rules+openmed` pipeline and documented suites.

# Local Rules And OpenMed Pipeline Audit

Date: 2026-06-16

## Why This Audit Happened

The app had drifted into a rules-only prototype while the earlier decon work had already shown the
right production shape: deterministic regex/rules plus OpenMed PHI-NER. The rules-only validation
gates passed large synthetic suites but missed obvious clinician prose, including repeated names,
legal-name labels, Spanish repeated names, and multi-patient sibling text.

## Prior Work We Reused

The copied `from-cds-eval` work found:

- OpenMed SuperClinical PHI-NER is local, deterministic, and roughly twice as fast as Haiku API
  decon in the small parity run.
- OpenMed alone missed an MRN-like value, so deterministic regex/rule guards are still required.
- OpenMed plus regex did well on canonical PHI, but previous 1,132-query analysis found recurring
  weaknesses in implicit references, multi-patient queries, Spanish PHI, URL-embedded usernames,
  practice/insurance names, nicknames, and temporal identifiers.

That means local rules should not grow into an unbounded fake NER model. They should provide:

- hard deterministic guards for MRNs, dates, phones, emails, URLs, addresses, schools, practices,
  pharmacies, IDs, and known workflow labels;
- clinical preservation/generalization rules such as DOB-to-age, A1c-to-elevated-A1c, BMI-to-range,
  and safe family relationship context;
- fallback residual-risk checks; and
- a stable replacement/rendering layer shared by OpenMed spans.

OpenMed should provide the broader free-text PHI layer, especially ordinary names and organization
spans that are too open-ended for reliable regex.

## Local Rules Reviewed

The current rules are grouped roughly as:

- prompt injection removal
- contextual uniqueness markers
- address/unit/location/school/camp/practice/pharmacy detection
- email, obfuscated email, phone, word-spelled phone, SSN
- chart/member/account/license/MRN identifiers
- URLs and MyChart-style paths
- insurance names
- exact dates and relative dates
- age and DOB-derived age
- lab/body-measurement generalization
- relationship and patient-name propagation
- residual high/medium risk checks
- destination-specific safe query rendering

## Problems Found In This Audit

- `Ste` in the address unit rule matched inside `steroid`, turning `stress-dose steroid guidance`
  into `stress-dose [ADDRESS] guidance`.
- The case-insensitive school-name rule ate lowercase clinical text such as
  `asthma and needs albuterol school form`.
- `MR # LP202408432` could lose to the hash-unit address rule and become `MR [ADDRESS]`.
- Patient-name propagation did not learn names from `Per MOC Jennifer, Lia and sibling Omar...`.
- Patient-name propagation did not learn repeated Spanish patient names from `La mama de Sofia...`.
- `Legal name Rowan Smith` was not treated as a name label.
- `FOC Carlos reports Mateo at Room 12B...` did not identify the patient name before `at`.
- `chart says Addison Ford, DOB...` did not remove the chart name while preserving the clinical
  eponym `Addison disease`.
- The first real `rules+openmed` current-suite run over-scrubbed `Kawasaki` when OpenMed tagged
  the disease eponym as a `name`, causing missing-critical-fact failures despite 0 PHI leaks.

## Fixes Made

- Added `MR # ...` as a full MRN span before hash-unit address detection.
- Tightened unit/address detection so `Ste` requires a unit-style token, not a word prefix.
- Tightened school detection to proper-cased school names, including forms like
  `Adena Middle School` and `Cedar Ridge Elementary`.
- Added patient-name introduction/propagation for multi-patient sibling phrasing.
- Added patient-name introduction/propagation for Spanish relation phrasing.
- Added `legal name` label handling.
- Added `at` as a caregiver-reported patient-name follower.
- Added `chart says [full name], DOB...` handling.
- Added an OpenMed adapter shield for clinical eponyms such as `Kawasaki` and `Addison disease`
  when the model classifies them as names.

## OpenMed Fit

The app now has an explicit engine boundary:

- `auto`: default. Uses `rules+openmed` only when local model setup says the OpenMed model is
  installed; otherwise uses `local-rules`.
- `local-rules`: deterministic rules only.
- `rules+openmed`: deterministic rules plus OpenMed spans. If explicitly requested and OpenMed is
  missing or cannot load locally, the result becomes high risk and copy is blocked.

The OpenMed adapter is optional and local-only. It uses local model files via `transformers` with
`local_files_only=True`; it does not download during decon. When loaded, it maps model entity labels
into the same categories as local rules, so replacement, risk scoring, and destination rendering are
shared.

Current environment note:

- OpenMed model files have been copied into the repo at
  `package/local-models/OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1/`.
- The model directory is ignored by git because it is approximately 1.6 GB.
- Default `python3` on this machine does not have `transformers`, so `auto` correctly falls back
  to `local-rules` there.
- `/Users/dochobbs/Downloads/Consult/cds-eval/.venv/bin/python` has `transformers` and `torch`
  and can load the copied model locally.
- Explicit `rules+openmed` requests fail closed when the model files or runtime are unavailable:
  the result reports the fallback reason, marks risk high, and blocks copy.

The intended pipeline is:

```text
deterministic regex/rules
  -> OpenMed PHI-NER
  -> residual risk scan
  -> optional reviewer/fallback for hard cases only
```

## New Seed-Gold Gate

The 10 difficult clinician snippets are now durable:

```text
package/data/decon_clinician_seed_gold_10_2026-06-16.json
```

Run:

```bash
PYTHONPATH=package/src /path/to/python-with-transformers \
  package/scripts/run_validation.py --suite clinician-seed-gold --engine rules+openmed
```

Current result:

```text
10 source cases
30 destination outputs
0 PHI leaks
0 missing clinical facts
100% clinical usability
100% handoff usability
```

## Model-Backed Verification

Focused OpenMed smoke:

```text
Input: Mom (Maria) says little Yael has fever for 5 days, red eyes, and rash. Could this be Kawasaki?
Engine: rules+openmed
Output: parent says [NICKNAME] has fever for 5 days, red eyes, and rash. Could this be Kawasaki?
```

Fresh verification on 2026-06-16:

| Command | Result |
| --- | --- |
| `python3 -m pytest package/tests` | `125 passed` |
| `package/scripts/run_validation.py --suite clinician-seed-gold --suite phi-field-prose --suite validation-blindspot-redteam --suite validation-blindspot-redteam-r2 --engine rules+openmed` | `231 / 231` outputs safe, clinically usable, and handoff usable; `0` PHI leaks |
| `package/scripts/run_validation.py --engine rules+openmed` | `3,150 / 3,150` outputs safe, clinically usable, and handoff usable; `0` PHI leaks |

The full current `rules+openmed` gate reported max average runtime `100.098 ms` and max p95 runtime
`123.279 ms` after model load.

## Remaining Risk

This is better, but not enough for a broad trust claim. The copied model proves the local pipeline
can run on this machine, but the Mac installer still needs to create the runtime and populate
`package/local-models/` automatically. The next validation step should compare future seed-gold
additions under:

- `local-rules`
- `rules+openmed` with the actual model installed
- optional future local LLM reviewer for semantic family/context edge cases

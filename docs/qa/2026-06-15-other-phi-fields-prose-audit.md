# Other PHI Fields Prose Audit

Date: 2026-06-15

## Why This Audit Happened

After the live-server Marvin note leaked a first-name-only patient mention, we audited adjacent
PHI classes for the same failure mode: fields that are obvious to a clinician but embedded in
narrative prose rather than clean labels.

## Initial Misses Found

The first 24-case non-name sweep found 9 leak classes:

- Month-name DOB prose left the year behind: `Date of birth is March 15, 2013`.
- `Born March 15, 2013` left the year behind.
- `Birthday is March 15, 2013` left the year behind.
- Future/relative weekdays survived: `Monday`, `Tuesday`, `next Wednesday`.
- Unlabeled spaced phone digits survived: `5 1 2 5 5 5 9 3 7 4`.
- Unlabeled obfuscated email survived: `marvin dot family at example dot com`.
- Pharmacy plus street/city survived: `Walgreens on Vernon in Adena`.
- Named school survived: `Adena Middle School`.
- Named camp survived: `Camp Lakeview`.

A follow-up 25-case sweep also caught one remaining name-adjacent bridge leak:

- `Mother Jennifer reports Marvin...` removed the caregiver name but initially left the patient
  first name.

The resulting reproducible suite is saved at:

```text
package/data/decon_phi_field_prose_25_2026-06-15.json
```

## Fixes Added

- Expanded DOB labels to include `birthdate` and `birthday`.
- Added month-day-year parsing so parseable DOB prose becomes age, not a bare placeholder.
- Added relative weekday/date stripping for current, last, this, and next weekdays.
- Added generic obfuscated-email detection.
- Added unlabeled spaced-phone detection.
- Added named pharmacy, school, and camp rules.
- Generalized schools to `elementary school`, `middle school`, `high school`, or `school`.
- Preserved generic camp context while stripping named camps and exact camp dates.
- Added caregiver-name bridge propagation for patterns such as
  `Mother Jennifer reports Marvin had...`.

## Clinical Utility Checks

The focused regression requires useful clinical facts to survive, including:

- derived age from DOB
- ADHD/anxiety medication context
- guanfacine dose and morning timing
- school transition context as `middle school`
- generic camp/trip context
- asthma, renal dosing, pregnancy medication, and vaccine context in the broader sweep

## Verification

Focused regression:

```text
python3 -m pytest package/tests/test_local_rules.py::test_decontextualize_text_removes_common_non_name_phi_prose
1 passed
```

Field sweep:

```text
python3 package/scripts/run_validation.py --suite phi-field-prose
25 source cases, 75 outputs, 0 PHI leaks, 0 missing clinical facts
75 / 75 clinically usable and handoff usable
```

Full package tests:

```text
python3 -m pytest package/tests
101 passed
```

Default validation gate:

```text
python3 package/scripts/run_validation.py
1,000 source cases, 3,000 outputs, 0 PHI leaks, 0 missing clinical facts
```

Persona regression gate:

```text
python3 package/scripts/run_validation.py --suite persona-regression
2,000 source cases, 6,000 outputs, 0 PHI leaks, 0 missing clinical facts
```

## Remaining Non-Claims

This still does not make V1 HIPAA-exhaustive. Known remaining classes needing explicit future
coverage include license numbers, device IDs, vehicle IDs, account numbers, certificate numbers,
IP addresses, images, biometric identifiers, and high-uniqueness narrative combinations.

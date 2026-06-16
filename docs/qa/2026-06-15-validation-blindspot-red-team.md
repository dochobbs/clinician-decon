# Validation Blind-Spot Red-Team

Date: 2026-06-15

## Why This Exists

The earlier aggregate validation gates reported 6,000 / 6,000 persona-regression outputs as safe,
but the live server still leaked the simple first-name-only note prose `Marvin`. That means the
validation set was too easy in at least one clinically common dimension.

This pass deliberately red-teams the validation process, not just the local rules.

## New Suite

```text
package/data/decon_validation_blindspot_redteam_17_2026-06-15.json
```

Run:

```bash
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam
```

## Initial Red Run

The first run against the pre-fix rules failed hard:

```text
Source cases: 17
Outputs: 51
Safe outputs: 13 / 51
PHI leaked outputs: 38 / 51
Missing-critical-fact outputs: 12 / 51
Clinically usable outputs: 39 / 51
Handoff usable outputs: 9 / 51
```

## Failure Classes

- Caregiver prose with common verbs leaked patient first names:
  - `Mom says Marvin...`
  - `Mother notes Marvin...`
  - `Dad states Marvin...`
  - `Caller Jennifer says Marvin...`
- Name-label prose leaked:
  - `Preferred name: Marvin`
  - `Name: Marvin Johnson`
  - `Patient named Marvin`
- DOB formats were under-covered:
  - `DOB: 03.15.2013`
  - `DOB March 15 2013`
  - `DOB 15 Mar 2013`
- Identifier classes from the previous "remaining gaps" list leaked:
  - policy ID
  - driver license number
  - IP address
  - apartment/unit fragment after a street address

## Fixes Added

- Generalized caregiver/caller reporting patterns with guarded patient-name propagation.
- Added caller/caregiver name removal before report verbs.
- Added explicit `Preferred name`, `Name`, and `Patient named` handling.
- Added dotted numeric DOB parsing.
- Added month-day-year-without-comma and day-month-year DOB parsing.
- Added policy/account/license/certificate/device/serial identifier patterns.
- Added IP-address stripping.
- Added apartment/unit/suite address-fragment stripping.
- Prevented relationship words such as `Dad` from being treated as patient names at sentence start.

## Final Verification

Focused gate:

```text
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam
51 / 51 safe, clinically usable, and handoff usable
0 PHI leaks
0 missing clinical facts
```

Regression gates also reran clean:

```text
python3 package/scripts/run_validation.py --suite phi-field-prose
75 / 75 safe, clinically usable, and handoff usable

python3 package/scripts/run_validation.py
3,000 / 3,000 safe, clinically usable, and handoff usable

python3 package/scripts/run_validation.py --suite persona-regression
6,000 / 6,000 safe, clinically usable, and handoff usable

python3 -m pytest package/tests
102 passed
```

## Hardening Lesson

The validation set needs clinician-authored adversarial probes in addition to generated volume.
Large synthetic counts are not enough if they do not include ordinary note prose and labels that
clinicians actually paste from charts.

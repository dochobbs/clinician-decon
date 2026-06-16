# Validation Blind-Spot Red-Team R2

Date: 2026-06-15

## Why This Exists

After the first validation blind-spot pass, we kept testing with more ordinary note phrasing and
label variants. The goal was to find places where aggregate validation could still pass while
clinicians could paste common chart prose that leaked identifiers.

## New Suite

```text
package/data/decon_validation_blindspot_redteam_r2_25_2026-06-15.json
```

Run:

```bash
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam-r2
```

## Initial Red Run

The first R2 run failed:

```text
Source cases: 25
Outputs: 75
Safe outputs: 19 / 75
PHI leaked outputs: 56 / 75
Missing-critical-fact outputs: 12 / 75
Clinically usable outputs: 63 / 75
Handoff usable outputs: 13 / 75
```

## Failure Classes

- Caregiver prose variants:
  - `Mom says that Marvin...`
  - `Mother reports that Marvin...`
  - `Per mom Jennifer, Marvin...`
  - `Per mother, Marvin...`
  - `Marvin, per mother,...`
- Name-label variants:
  - `Child's name is Marvin`
  - `Patient goes by Marvin`
  - `Alias: Marvin`
  - lowercase `patient name: marvin johnson`
  - lowercase `preferred name: marvin`
- Parent abbreviations:
  - `MOC Jennifer says Marvin...`
  - `FOC Carlos reports Marvin...`
- DOB formats:
  - `DOB 3 15 2013`
  - `DOB 2013/03/15`
  - `DOB Mar. 15, 2013`
  - `DOB 15 Mar. 2013`
- Identifier and location variants:
  - `MR # LP202408432`
  - `Chart ID CH 884422`
  - `Room 12B at school`
  - `123 Oak Street #5B`
  - word-spelled phone numbers

## Fixes Added

- Optional `that` in caregiver-reporting patient-name propagation.
- `per caregiver` and `patient, per caregiver` patient-name propagation.
- `MOC` / `FOC` handling and parent generalization.
- Lowercase and alias-style name labels.
- `Child's name is` and `Patient goes by` handling.
- Space-separated, ISO-slash, and abbreviated-period DOB parsing to derived age.
- `MR #` pattern support and chart IDs with internal spaces.
- Room-number, hash-unit, and word-spelled phone stripping.
- Safer short web-search fallback after removing a word-spelled phone number.
- Caregiver-name grammar cleanup so web-search queries do not keep orphaned phrasing like
  `says that had` after removing a patient name.

## Final Verification

Focused gate:

```text
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam-r2
75 / 75 safe, clinically usable, and handoff usable
0 PHI leaks
0 missing clinical facts
```

Regression gates:

```text
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam
51 / 51 safe, clinically usable, and handoff usable

python3 package/scripts/run_validation.py --suite phi-field-prose
75 / 75 safe, clinically usable, and handoff usable

python3 package/scripts/run_validation.py
3,000 / 3,000 safe, clinically usable, and handoff usable

python3 package/scripts/run_validation.py --suite persona-regression
6,000 / 6,000 safe, clinically usable, and handoff usable

python3 -m pytest package/tests
104 passed
```

## Hardening Lesson

The validation process still needs repeated clinician-authored adversarial sets. Generated volume
is useful, but terse clinical prose, lowercase labels, and workflow-specific abbreviations are where
simple deterministic decon rules are most likely to miss.

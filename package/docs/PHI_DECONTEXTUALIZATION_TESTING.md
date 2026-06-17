# PHI Decontextualization Testing Report

**Date:** 2026-06-17
**Component:** local decontextualization and validation pipeline
**Purpose:** Verify that expected PHI is removed while clinically necessary facts remain usable.

## Architecture Under Test

```text
clinical query or note
  -> deterministic rules
  -> optional local PHI-NER model
  -> residual risk scan
  -> destination-specific prompt/query output
```

## Validation Approach

For each synthetic case:

1. Run the source text through the decon pipeline.
2. Compare the output with expected PHI terms.
3. Check required clinical facts are still present.
4. Confirm copy is blocked when residual PHI remains.
5. Record category-level failures for regression.

## PHI Categories

The current suites cover:

- names, nicknames, relatives, and provider names
- MRNs, chart IDs, account IDs, claims, accessions, serials, and other identifiers
- DOBs, exact dates, relative dates, and exact ages
- phone numbers, emails, URLs, IP addresses, and device/network identifiers
- street addresses, ZIP-level geography, schools, camps, facilities, rooms, units, beds, and floors
- prompt-injection attempts and uniqueness phrases
- clinical eponym collisions and name/drug collisions

## Clinical Utility Categories

The evaluator checks that useful facts remain, including:

- medication names and doses
- triage symptoms
- severe labs and criteria-relevant values
- broad age bands
- weight when needed for dosing
- diagnoses and clinical eponyms
- vaccine and preventive-care topics
- renal, pregnancy, asthma, allergy, behavioral-health, and rare-disease contexts

## Example Cases

| Input pattern | Expected safe behavior |
| --- | --- |
| `Patient name + DOB + MRN + phone` | remove direct identifiers and preserve clinical topic |
| `DOB 3/15/2013` | convert to age band |
| `exact age 13` | convert to broader age band |
| `Addison Brooks has Addison disease` | remove name, preserve diagnosis |
| `Only HLH patient on 7th floor today` | remove uniqueness/floor/date, preserve rare condition |
| `A1c 8.2 and BMI 31` | generalize when exact values are unnecessary |
| `weight 28 kg, epinephrine dose?` | preserve exact weight because dosing depends on it |

## Current Gate

The current gate is documented in:

```text
docs/qa/headless-validation.md
```

Current snapshot:

```text
1,050 source cases
3,150 destination outputs
0 PHI leaks
0 missing clinical facts
100% handoff usable
```

## Known Boundaries

- Synthetic validation does not prove universal safety on real notes.
- The tool is a PHI-minimization aid, not a legal de-identification guarantee.
- Outputs still require human review before external use.
- A technically safe output can still be clinically useless if the source text contains no
  clinical question.

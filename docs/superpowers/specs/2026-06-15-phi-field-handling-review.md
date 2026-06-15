# PHI Field Handling Review

Date: 2026-06-15

This note records the first field-by-field review after the initial local app run showed that
identifier stripping could also remove useful clinical intent.

## Review Principle

Not every PHI-like span should become an empty placeholder. The local app should distinguish:

- Direct identifiers that should disappear: names, MRNs, phone numbers, email, SSN, URLs,
  street addresses, ZIP-level geography.
- Clinically useful derived facts that should survive in safer form: age, coarse timing,
  relationships, and broad clinical measurements.
- High-uniqueness facts that need future expert review before preservation: rare geography,
  exact dates, rare diagnoses combined with demographics, unusual narrative details.

## Current V1 Local Rules

- Name: replaced with `[NAME]`. Relative names become generalized relationships because the
  relationship can matter but the name is unsafe.
- MRN/record ID: replaced with `[MRN]`; no clinical utility is preserved.
- Phone/email/SSN/URL: replaced with placeholders; no clinical utility is preserved.
- DOB: removed as a date, but converted to age when parseable.
- Age under 90: normalized, e.g. `52yo` to `52-year-old`.
- Age 90 or older: normalized to `90 or older`.
- Relative dates: converted to coarse timing, e.g. `today` to `same-day`.
- Clinical values: generalized, e.g. `A1c 8.2` to `elevated A1c`.
- Relative/caregiver names: name is removed while relationship context remains, e.g.
  `Wife Linda` to `spouse`.
- Street/geography: street address and city/state/ZIP patterns are removed.

## Regression Cases Added

- Vaccine search from DOB now produces
  `13-year-old pediatric immunization schedule vaccines current guidelines`.
- Explicit ages normalize and age 90+ is aggregated.
- A1c values keep clinical meaning without exact numeric value.
- Spouse/relative names do not leak while relationship context remains.
- Street address plus city/state/ZIP is removed.

## Remaining Gaps

- City/state parsing is still pattern-based and incomplete.
- No robust detection yet for license numbers, device IDs, vehicle IDs, account numbers,
  certificate numbers, IP addresses, images, or biometric identifiers.
- Rare disease plus exact demographic combinations still need a local model or reviewer pass.
- Exact clinical values may need mode-specific controls: some queries need exact creatinine,
  weight, gestational age, or medication dose.
- The UI should expose an age precision control: age band by default, exact age when clinically
  needed, and forced `90 or older` for older adults.

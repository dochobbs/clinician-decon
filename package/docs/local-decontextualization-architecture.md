# Local Decontextualization Architecture

**Date:** 2026-06-17
**Component:** local PHI minimization layer for clinical AI and search handoffs

## Problem

Clinicians often need to ask an external AI or search tool a clinical question, but the source text
may include patient identifiers or local workflow context. The destination usually needs the
clinical topic, not the patient identity.

Example input:

```text
Marcus Johnson, DOB 3/15/2013, MRN LP-2024-08432, needs vaccine guidance.
```

Useful decontextualized output:

```text
adolescent immunization schedule vaccines current guidelines
```

The decontextualization layer bridges that gap.

## Architecture

```text
clinical text
  -> deterministic rules
  -> optional local PHI-NER model
  -> residual risk scan
  -> destination-specific prompt/query shaping
  -> reviewed safe prompt
```

## Layer 1: Deterministic Rules

Purpose:

- catch high-confidence identifiers quickly
- normalize common clinical-safe replacements
- preserve useful clinical context when possible

Examples:

- phone number -> `[PHONE]`
- MRN -> `[MRN]`
- DOB -> age band
- exact relative date -> coarse timing
- exact A1c -> `elevated A1c` when exact value is unnecessary

## Layer 2: Local PHI-NER

Purpose:

- catch names and identifiers missed by deterministic patterns
- improve recall on prose and mixed formats
- run locally without sending raw text to a network service during decon

The model-backed engine must load model files locally. If the model-backed engine is explicitly
requested but unavailable, the app should fail closed rather than silently presenting a release
gate as passed.

## Layer 3: Residual Risk Scan

Purpose:

- inspect the cleaned output for leftover high-risk patterns
- block copy when obvious identifiers remain
- surface actionable reasons such as likely MRN, URL, phone, date, or location

This scan happens after both deterministic rules and optional model spans.

## Layer 4: Destination-Specific Handoff

Different destinations need different output shape:

- external LLM: richer de-identified clinical context
- external search: short de-identified query
- copy only: reviewed prompt without opening a destination

The app copies text to the clipboard and opens only the destination home page or search surface.
Prompt text should not be embedded in a URL.

## Data Handling

| Data type | Local rules | Local model | External destination |
| --- | ---: | ---: | ---: |
| Raw input text | yes | yes, if installed | no |
| Removed values | no display | no display | no |
| Removed categories | yes | yes | optionally in UI only |
| Safe prompt | yes | yes | user-controlled copy/paste |

## Examples

| Input | Safe output |
| --- | --- |
| `DOB 3/15/2013` | `adolescent` |
| `MRN LP-2024-08432` | `[MRN]` |
| `Mom Jennifer called from 512-555-0147` | `parent called from [PHONE]` |
| `A1c 8.2 and BMI 31` | `elevated A1c and obesity-range BMI` |
| `Only HLH patient on 7th floor today` | `Rare HLH case` with floor/date removed |

## Non-Goals

- no claim of universal legal de-identification
- no hidden automatic posting to external tools
- no display of removed PHI values
- no network model call during decon

## Release Gate

The release gate is documented in:

```text
docs/qa/headless-validation.md
```

It checks both:

- safety: expected PHI does not survive
- utility: required clinical facts remain present

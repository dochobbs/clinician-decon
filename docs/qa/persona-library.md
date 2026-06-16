# Synthetic Persona Library

Date: 2026-06-15

The persona library lives at:

```text
package/data/personas/v1.json
```

It is the shared vocabulary for generating higher-quality synthetic traces. The point is to
avoid random low-value examples while still scaling beyond a small hand-authored gold set.

The first generator that consumes this library is:

```text
package/scripts/generate_traces.py
```

Its first checked-in generated suite is:

```text
package/data/decon_persona_regression_2000_2026-06-15.json
```

## What It Contains

The `v1` library has four sections:

| Section | Count | Purpose |
| --- | ---: | --- |
| `clinician_personas` | 9 | Who is asking and what kind of clinical fidelity they will notice. |
| `patient_context_personas` | 13 | Clinical scenarios where PHI removal and fact preservation can conflict. |
| `source_channel_personas` | 8 | Where the pasted text came from, such as EHR copy, portal thread, OCR, or web search. |
| `perturbation_profiles` | 8 | Noise and adversarial transformations applied to otherwise coherent cases. |

Every clinician, patient/context, and source-channel persona declares:

- `trace_goals`
- `phi_risks`
- `clinical_preservation_risks`
- `archetype_tags`

Perturbation profiles declare:

- where they apply
- what transformations they add
- which failure modes they are meant to catch

## Coverage Priorities

The first library emphasizes failure modes already seen in this project:

- DOB/exact-age conversion to clinical age bands without losing task-relevant age thresholds.
- Pediatric vaccine and weight-based dosing questions.
- Exact severe lab or dosing values that must not be over-generalized.
- Names that collide with clinical eponyms.
- Multi-patient sibling notes and relationship context.
- Spanish and mixed-language family phrasing.
- OCR-spaced MRNs, phones, and dotted labels.
- Prompt-injection attempts that ask the tool to retain identifiers.
- URLs, portal metadata, referral packets, and copied EHR headers.
- Web-search handoffs that must stay concise but clinically useful.

## How To Use It In Generation

A synthetic generator should choose a tuple like:

```json
{
  "clinician_persona": "pediatric-vaccine-planner",
  "patient_context_persona": "pediatric-catchup-vaccine-child",
  "source_channel_persona": "portal-message-thread",
  "perturbation_profiles": ["relationship-noise", "obfuscated-contact"]
}
```

Then it should fill known PHI slots and clinical slots from an archetype. The output trace should
record:

- selected persona IDs
- source archetype ID
- generated query
- expected PHI values
- forbidden terms
- required clinical facts
- perturbation IDs
- seed and reference date
- split, such as `dev`, `regression`, or `frozen-validation`

## Acceptance Rules

Generated traces should be rejected before entering a suite when:

- the clinical question becomes nonsensical
- a required clinical fact is absent from the source query
- an exact PHI value is also required as a clinical fact
- identifiers are copied from real examples
- the same query appears twice in the same suite
- the perturbation removes the clinical intent

This library supports scale, but it does not replace clinician-reviewed gold validation.

# Residual Identifier Red-Team and Pipeline Completeness

Date: 2026-09-02

## Outcome

The initial `rules+openmed` run exposed a real coverage gap: six of 12 source shapes failed, 17 / 36
destination outputs retained identifier material, and all 17 still allowed copying. The pipeline
was hardened with authoritative structured-field spans, propagation of confidently detected
identifiers, broader FHIR/HL7/JSON/OCR patterns, and a final partial-remnant guard.

The same suite now passes 36 / 36 outputs with zero PHI leaks, zero unsafe copy, and zero clinical
fact loss. The expanded release corpus also passes 10,761 / 10,761 outputs across 3,587 source
cases. This closes the known failure family; it does not prove that no unseen PHI form exists.

The initial failure was a coverage gap, not a contradiction of the earlier 9,513 / 9,513 result. Re-scoring the
3,171 earlier source cases with the stronger partial-fragment evaluator found no additional
leaks; those fixtures simply did not represent this failure family.

## Evaluator correction

The prior evaluator primarily searched output for the original PHI string. A partial model span
could therefore turn `ABCDEFGHIJK` into `[MRN]DEFGHIJK`: the exact source identifier was gone,
but most identifying material survived.

The evaluator now also detects long structured-PHI remnants when:

- a contiguous residual token preserves at least half the original value; or
- multiple visible fragments around placeholders preserve at least half the original value in
  source order, such as `POI[IDENTIFIER]QLK`.

The check is restricted to long identifier-shaped values containing digits or all-uppercase
characters. It does not apply substring matching to ordinary names or clinical prose.

## New product-level suite

Fixture: `package/data/decon_residual_identifier_redteam_12_2026-09-02.json`

The 12 synthetic cases cover unlabeled and labeled records, alphanumeric chart IDs, FHIR
resource IDs, HL7 PID fields, JSON, export filenames, OCR-spaced identifiers, repeated values,
compound account identifiers, two-identifier notes, and portal tokens. Every case also carries
critical clinical facts so safety cannot be improved by deleting the note.

### OpenMed-backed before and after

| Metric | Initial | Hardened |
| --- | ---: | ---: |
| Source cases | 12 | 12 |
| Destination outputs | 36 | 36 |
| Source shapes with at least one leak | 6 / 12 | 0 / 12 |
| PHI-leaked outputs | 17 / 36 | 0 / 36 |
| Unsafe copy-allowed outputs | 17 / 36 | 0 / 36 |
| Clinically usable outputs | 36 / 36 | 36 / 36 |
| Handoff-usable outputs | 19 / 36 (52.8%) | 36 / 36 (100%) |

Initial failing shapes:

- unlabeled uppercase patient record;
- FHIR patient resource ID;
- HL7 PID identifier;
- OCR-spaced record identifier;
- repeated identifier split around a placeholder;
- two long identifiers where one was only partially masked and the other survived.

Representative outputs included:

- `[MRN]DEFGHIJK` from `ABCDEFGHIJK`;
- `Patient/ABCDEF123456789` unchanged;
- `PID|1||LMNOPQRSTUVX^^^MRN||` unchanged;
- `[MRN] CD EF GH IJ KL` from an OCR-spaced record;
- `POI[IDENTIFIER]QLK` from `POIUYTREWQLK`.

### PPLX diagnostic arm

On this narrow structured-identifier suite, `rules+pplx` produced 36 / 36 safe, clinically usable,
and handoff-usable outputs. That does not reverse the larger recommendation: PPLX lost clinical
facts in 221 cases on the broader release corpus. It does show that PPLX may be valuable as an
asymmetric secondary detector for structured identifiers, provided `other_pii` cannot directly
remove clinical content.

## How close the pipeline is

The pipeline now has a strong synthetic regression boundary for its represented use cases. It is
appropriate to describe it as a robust beta, not as a mathematically complete privacy boundary.
The remaining uncertainty is primarily independent, clinician-reviewed real-world evidence.

| Capability | Current evidence | Readiness |
| --- | --- | --- |
| Common structured PHI and clinical preservation | Expanded 3,587-case release corpus: 10,761 / 10,761 safe and clinically complete outputs | Strong for represented cases |
| Partial and fragmented structured identifiers | Residual suite improved from 19 / 36 to 36 / 36 handoff usable | Known gap closed |
| Cross-turn recurrence | Improved from 750 / 780 to 780 / 780 handoff usable | Known gap closed; still synthetic |
| Clean clinical preservation | 48 matched structured controls plus existing clean controls retained every labeled fact | Strong but synthetic |
| Final-output fail-closed validation | Targeted tests verify partial remnants are detected and copying is blocked | Implemented |
| Real-world generalization | Mostly synthetic and templated fixtures | Insufficient evidence |

A percentage would imply more certainty than the evidence supports. The architecture and regression
coverage are now substantially stronger; a strong production privacy claim still needs blinded,
clinician-reviewed material not used to write the rules.

## Completion criteria

Completed engineering criteria:

1. Make deterministic structured-field spans authoritative over shorter model spans.
2. Detect and remove—or fail closed on—residual identifier fragments in the final rendered output.
3. Cover FHIR, HL7, OCR-spaced, filename, portal-token, repeated, and multi-ID shapes in the
   normal release gate.
4. Close the known cross-turn URL/name recurrence cases without reducing clinical preservation.

Remaining evidence criteria before describing the supported boundary as complete:

1. Add at least 250 clinician-reviewed clean clinical conversations, multilingual paraphrases,
   and long-window boundary cases.
2. Re-run a blinded set not used to write the rules, with zero unsafe-copy leaks and zero critical
   clinical-fact loss as the release threshold.

PPLX should remain an experimental comparison arm. The production direction is the hardened
rules-plus-OpenMed hybrid, followed by blinded external validation rather than another model swap.

## Reproduce

```bash
cd package
PYTHONPATH=src <model-python> -m decon.validation_cli \
  --suite residual-identifier-redteam \
  --destinations chatgpt,gemini,web_search \
  --reference-date 2026-06-15 \
  --engine rules+openmed \
  --report reports/residual-identifier-redteam-2026-09-02.json
```

Generated JSON reports remain ignored. This document, the fixture, scorer changes, and focused
tests are the durable evidence.

# Persona Regression 2,000-Case Eval

Date: 2026-06-15

Scope: deterministic persona-driven synthetic traces generated from:

- `package/data/personas/v1.json`
- `package/data/archetypes/v1.json`
- `package/scripts/generate_traces.py`

The generated suite is saved at:

```text
package/data/decon_persona_regression_2000_2026-06-15.json
```

## Generation

Command:

```bash
python3 package/scripts/generate_traces.py \
  --count 2000 \
  --seed 20260615 \
  --output package/data/decon_persona_regression_2000_2026-06-15.json \
  --report package/reports/persona-regression-2000-2026-06-15.json
```

Generation summary:

- Seed: `20260615`
- Reference date: `2026-06-15`
- Cases: `2,000`
- Clinical-labeled cases: `2,000`
- Cases with expected PHI: `2,000`
- Archetypes: `10`, with `200` cases per archetype

## Archetype Coverage

| Archetype | Cases |
| --- | ---: |
| `allergy-antibiotic-alternative` | 200 |
| `asthma-action-plan` | 200 |
| `hlh-severe-labs` | 200 |
| `pediatric-vaccine-catchup` | 200 |
| `portal-callback-triage` | 200 |
| `pregnancy-medication-safety` | 200 |
| `rare-disease-web-search` | 200 |
| `renal-dose-adjustment` | 200 |
| `sibling-multipatient-note` | 200 |
| `weight-based-dosing` | 200 |

## Source Channel Coverage

| Source channel | Cases |
| --- | ---: |
| `ehr-summary-copy` | 398 |
| `web-search-box` | 333 |
| `phone-call-note` | 324 |
| `portal-message-thread` | 324 |
| `json-chart-fragment` | 205 |
| `dictation-transcript` | 148 |
| `ocr-chart-export` | 140 |
| `referral-packet` | 128 |

## Perturbation Coverage

| Perturbation | Cases |
| --- | ---: |
| `canonical-clean` | 477 |
| `section-header-note` | 362 |
| `relationship-noise` | 311 |
| `clinical-lookalike` | 247 |
| `obfuscated-contact` | 215 |
| `prompt-injection` | 176 |
| `url-embedded-phi` | 157 |
| `ocr-spacing` | 55 |

## First Run Failure

The first validation run exposed real local-rule gaps:

```text
Source cases: 2000
Outputs: 6000
PHI leaked outputs: 2742
Unsafe copy-allowed leaks: 2742
Clinical labeled outputs: 6000
Clinically usable outputs: 6000
Clinical usability rate: 100.00%
Handoff usability rate: 54.30%
```

The main failure categories were:

- JSON chart fragments preserving `"patient_name":"Full Name"`.
- Phone notes preserving `caller <Name> at <PHONE>`.
- Relationship-noise prompts preserving `sibling <Name> is worried`.
- OCR-spaced alphanumeric MRNs such as `M R N L P 2 0 2 5 4 0 0 0 0`.

After fixing the first three name patterns, the suite still found:

```text
PHI leaked outputs: 531 / 6000
Clinical usability rate: 100.00%
Handoff usability rate: 91.15%
```

Those remaining leaks were all spaced alphanumeric MRNs, concentrated in the HLH/severe-labs
and rare-disease web-search archetypes because those were the archetypes using `ocr-chart-export`
and `ocr-spacing`.

## Final Validation

Command:

```bash
python3 package/scripts/run_validation.py \
  --suite persona-regression \
  --report package/reports/persona-regression-validation-2026-06-15.json
```

Final result:

```text
Decon validation PASS
Suites: persona-regression
Destinations: llm_primary, llm_secondary, web_search
Source cases: 2000
Outputs: 6000
PHI leaked outputs: 0
Unsafe copy-allowed leaks: 0
Clinical labeled outputs: 6000
Clinically usable outputs: 6000
Clinical usability rate: 100.00%
Handoff usability rate: 100.00%
Max avg runtime: 0.289 ms
Max p95 runtime: 0.399 ms
```

Every destination had `2,000 / 2,000` PHI-safe outputs and `2,000 / 2,000` clinically usable
outputs.

## Interpretation

The suite did what it was supposed to do: it converted prior learning into reproducible
synthetic traces, then found failure modes that the smaller suites did not exercise strongly
enough.

The important signal is not only the final zero-leak run. The important signal is that failures
were traceable back to source channel and perturbation choices:

- `json-chart-fragment` drove JSON patient-name fixes.
- `phone-call-note` drove caller-name fixes.
- `relationship-noise` drove sibling-name fixes.
- `ocr-chart-export` plus `ocr-spacing` drove alphanumeric spaced-MRN fixes.

This makes the generated suite useful as a regression gate and as a design tool for the next
round of clinician-reviewed archetypes.

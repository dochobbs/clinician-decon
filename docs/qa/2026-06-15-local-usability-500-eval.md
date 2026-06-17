# Local Decon 500-Case Usability Eval

Date: 2026-06-15

Scope: freshly generated 500 synthetic clinician queries run through the current local
`package/src/decon/local_rules.py` engine. Each query includes expected PHI and required
clinical facts so the eval checks both safety and whether the decontextualized prompt
remains useful for an outside LLM or web search.

- Seed: `20260615`
- Reference date: `2026-06-15`
- Cases: `500`
- Destinations: `llm_primary, llm_secondary, web_search`
- Outputs evaluated: `1500`
- Average runtime: `0.153 ms`
- p95 runtime: `0.219 ms`

## Headline

| Metric | Outputs | Rate |
| --- | ---: | ---: |
| PHI-safe outputs | 1500 / 1500 | 100.0% |
| Clinically usable outputs | 1500 / 1500 | 100.0% |
| Handoff usable outputs | 1500 / 1500 | 100.0% |
| Outputs with PHI leaks | 0 / 1500 | 0.0% |
| Outputs missing critical facts | 0 / 1500 | 0.0% |
| Unsafe copy allowed outputs | 0 / 1500 | 0.0% |

Definitions:

- `PHI-safe`: copied output did not contain any expected synthetic PHI term.
- `Clinically usable`: copied output retained all required clinical facts for the case.
- `Handoff usable`: output was PHI-safe, clinically usable, and copy was allowed.

## Destination Breakdown

| Destination | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts | Unsafe copy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `llm_primary` | 500 | 500 | 500 | 500 | 0 | 0 | 0 |
| `llm_secondary` | 500 | 500 | 500 | 500 | 0 | 0 | 0 |
| `web_search` | 500 | 500 | 500 | 500 | 0 | 0 | 0 |

## Category Breakdown

| Category | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `allergy_antibiotic` | 84 | 84 | 84 | 84 | 0 | 0 |
| `asthma_action` | 108 | 108 | 108 | 108 | 0 | 0 |
| `dictation_buried_phi` | 9 | 9 | 9 | 9 | 0 | 0 |
| `epi_weight` | 120 | 120 | 120 | 120 | 0 | 0 |
| `lab_severity` | 144 | 144 | 144 | 144 | 0 | 0 |
| `med_titration` | 159 | 159 | 159 | 159 | 0 | 0 |
| `no_phi_guideline` | 63 | 63 | 63 | 63 | 0 | 0 |
| `pediatric_weight_dosing` | 147 | 147 | 147 | 147 | 0 | 0 |
| `pregnancy_med` | 111 | 111 | 111 | 111 | 0 | 0 |
| `red_flag` | 135 | 135 | 135 | 135 | 0 | 0 |
| `renal_dosing` | 120 | 120 | 120 | 120 | 0 | 0 |
| `screening_guideline` | 126 | 126 | 126 | 126 | 0 | 0 |
| `vaccine_schedule` | 174 | 174 | 174 | 174 | 0 | 0 |

## Missing Clinical Signal

No required clinical facts were missing in the current run.

Top categories for missing clinical signal:

No category had missing required clinical facts in the current run.

## PHI Leak Signal

No expected synthetic PHI terms leaked in the current run.

## Representative Usability Failures

None in the current run.


## Representative PHI Failures

None in the current run.


## Interpretation

This suite intentionally asks a harder question than the prior PHI-only sweeps: is the
prompt still clinically useful after decontextualization? The main usability risk is
over-generalizing exact values that are clinically necessary for dosing, severity, or
criteria checks.

The product should treat these failures differently from pure PHI leaks. A PHI leak is
a safety blocker. Missing critical facts are a quality blocker: the output may be safe
to paste, but the clinician would get a weaker or wrong answer because dose, weight,
lab severity, or diagnostic details were stripped.

The first run of this suite was intentionally useful because it failed. It found 415
outputs with missing critical facts and 9 copy-allowed PHI leaks. The dominant signal-loss
failures were exact pediatric weight for dosing and exact lab severity for HLH-style
criteria checks. The PHI leaks were dictation-style phrases with `patient number ...`,
followed by a name and date of birth. The current run is clean after adding targeted
rules for those cases.

This does not prove the product is clinically safe. It proves the current deterministic
rules preserve the required facts for this generated suite. The next useful expansion is
a clinician-authored adversarial set where the required clinical facts are reviewed by a
physician, especially for drug dosing, growth/weight, pregnancy, oncology/rare disease,
and multi-patient notes.

## Reproduction

```bash
python3 package/scripts/run_usability_eval.py
```

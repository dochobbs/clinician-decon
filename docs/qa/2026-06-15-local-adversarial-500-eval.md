# Local Decon 500-Case Adversarial Eval

Date: 2026-06-15

Scope: deterministic adversarial synthetic queries run through the current local
`package/src/decon/local_rules.py` engine. This suite targets common product failure
modes that are easy to miss in broad randomized PHI sweeps: prompt-injection text,
buried patient identity, eponym collisions, repeated sibling names, OCR-spaced
identifiers, URL-embedded PHI, Spanish family phrasing, small-town uniqueness,
copy-pasted note sections, and contact/date mashups.

- Seed: `20260615`
- Reference date: `2026-06-15`
- Cases: `500`
- Destinations: `chatgpt, gemini, web_search`
- Outputs evaluated: `1500`
- Average runtime: `0.234 ms`
- p95 runtime: `0.315 ms`

## Headline

| Metric | Outputs | Rate |
| --- | ---: | ---: |
| PHI-safe outputs | 1500 / 1500 | 100.0% |
| Clinically usable outputs | 1500 / 1500 | 100.0% |
| Handoff usable outputs | 1500 / 1500 | 100.0% |
| Outputs with PHI leaks | 0 / 1500 | 0.0% |
| Outputs missing critical facts | 0 / 1500 | 0.0% |
| Unsafe copy allowed outputs | 0 / 1500 | 0.0% |

## Destination Breakdown

| Destination | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts | Unsafe copy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `chatgpt` | 500 | 500 | 500 | 500 | 0 | 0 | 0 |
| `gemini` | 500 | 500 | 500 | 500 | 0 | 0 | 0 |
| `web_search` | 500 | 500 | 500 | 500 | 0 | 0 | 0 |

## Category Breakdown

| Category | Outputs | Safe | Clinically usable | Handoff usable | PHI leaked | Missing facts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `buried_patient_identity` | 141 | 141 | 141 | 141 | 0 | 0 |
| `copy_pasted_note` | 126 | 126 | 126 | 126 | 0 | 0 |
| `date_contact_mashup` | 153 | 153 | 153 | 153 | 0 | 0 |
| `eponym_collision` | 180 | 180 | 180 | 180 | 0 | 0 |
| `multi_patient_repeat` | 150 | 150 | 150 | 150 | 0 | 0 |
| `ocr_spaced_identifier` | 198 | 198 | 198 | 198 | 0 | 0 |
| `prompt_injection_override` | 153 | 153 | 153 | 153 | 0 | 0 |
| `small_town_unique` | 135 | 135 | 135 | 135 | 0 | 0 |
| `spanish_family` | 132 | 132 | 132 | 132 | 0 | 0 |
| `url_path_phi` | 132 | 132 | 132 | 132 | 0 | 0 |

## PHI Leak Signal

No expected synthetic PHI terms leaked in the current run.

## Missing Clinical Signal

No required clinical facts were missing in the current run.

## Representative PHI Failures

None in the current run.


## Representative Usability Failures

None in the current run.


## Reproduction

```bash
python3 package/scripts/run_adversarial_eval.py
```

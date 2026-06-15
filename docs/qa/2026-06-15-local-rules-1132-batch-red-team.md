# Local Rules 1,132-Case Batch Red-Team

Date: 2026-06-15

Scope: current `package/src/decon/local_rules.py`, evaluated against the gathered `cds-eval`
fixtures copied into this repo.

Fixtures:

- `from-cds-eval/data/decon_synth_500.json`
- `from-cds-eval/data/decon_synth_500_b.json`
- `from-cds-eval/data/decon_combined_1132.json`

Reference date: 2026-06-15.

Destinations tested:

- `chatgpt`: copied prompt is `destination_prompt`.
- `web_search`: copied prompt is `safe_query`.

Method:

- Run every fixture query through `decontextualize_text`.
- Compare the copied prompt against the fixture's expected `phi` terms.
- Count a leak when an expected PHI term survives as a standalone word or identifier.
- Count `Low+copy leak rows` when the output leaked an expected PHI term while reporting
  `risk: low` and `copy_allowed: true`.

## Headline

The current small local-rules prototype fails the larger suite. This is not the prior
OpenMed + regex stack; this is only the app prototype's lightweight deterministic rules.

| Fixture | Destination | Rows | PHI terms | Leaked terms | Leak rows | Low+copy leak rows | Runtime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `decon_synth_500.json` | `chatgpt` | 500 | 737 | 318 | 162 | 162 | 0.085s |
| `decon_synth_500.json` | `web_search` | 500 | 737 | 264 | 135 | 135 | 0.023s |
| `decon_synth_500_b.json` | `chatgpt` | 500 | 860 | 379 | 194 | 194 | 0.073s |
| `decon_synth_500_b.json` | `web_search` | 500 | 860 | 317 | 163 | 163 | 0.025s |
| `decon_combined_1132.json` | `chatgpt` | 1132 | 2526 | 1067 | 482 | 482 | 0.234s |
| `decon_combined_1132.json` | `web_search` | 1132 | 2526 | 915 | 409 | 409 | 0.244s |

## Post-Patch Delta: Learned Regex Port

After porting the deterministic lessons from `from-cds-eval/local_cds/decon.py` into
`package/src/decon/local_rules.py`, the two synthetic 500-query suites are back to zero detected
fixture leaks for both ChatGPT and Web Search handoffs.

Patch coverage added:

- broad name grammar: hyphenated, apostrophe, Latin-extended, and particle surnames
- compact age/sex normalization such as `35M` -> `35-year-old male`
- undashed SSN with context
- city/state without ZIP, city-only address tails, practice/facility names, and small-town context
- nickname, parenthetical family name, Spanish relation/name, sibling, and indirect relation phrases
- month/day temporal references and `last week`
- body measurements and lab value variants such as `A1c of 9.2`, `48,000`, and `45k`
- prompt-injection stripping before copy/open handoff

Post-patch run, same fixtures and reference date:

| Fixture | Destination | Rows | PHI terms | Leaked terms | Leak rows | Low+copy leak rows | Avg runtime | p95 runtime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `decon_synth_500.json` | `chatgpt` | 500 | 737 | 0 | 0 | 0 | 0.101 ms | 0.181 ms |
| `decon_synth_500.json` | `web_search` | 500 | 737 | 0 | 0 | 0 | 0.081 ms | 0.169 ms |
| `decon_synth_500_b.json` | `chatgpt` | 500 | 860 | 0 | 0 | 0 | 0.086 ms | 0.176 ms |
| `decon_synth_500_b.json` | `web_search` | 500 | 860 | 0 | 0 | 0 | 0.083 ms | 0.174 ms |
| `decon_combined_1132.json` | `chatgpt` | 1132 | 2526 | 268 | 101 | 89 | 0.113 ms | 0.368 ms |
| `decon_combined_1132.json` | `web_search` | 1132 | 2526 | 238 | 87 | 75 | 0.112 ms | 0.351 ms |

This is a material recovery from the bad app-local baseline:

| Fixture | Destination | Baseline leaked terms | Post-patch leaked terms | Baseline leak rows | Post-patch leak rows |
| --- | --- | ---: | ---: | ---: | ---: |
| `decon_synth_500.json` | `chatgpt` | 318 | 0 | 162 | 0 |
| `decon_synth_500.json` | `web_search` | 264 | 0 | 135 | 0 |
| `decon_synth_500_b.json` | `chatgpt` | 379 | 0 | 194 | 0 |
| `decon_synth_500_b.json` | `web_search` | 317 | 0 | 163 | 0 |
| `decon_combined_1132.json` | `chatgpt` | 1067 | 268 | 482 | 101 |
| `decon_combined_1132.json` | `web_search` | 915 | 238 | 409 | 87 |

Remaining combined-suite leaks are concentrated in Amboss stress rows. The largest residual buckets
are `amboss_r4_golden` and `amboss_r4_validation`, plus edge cases where the fixture labels exact
age, medication dose, disease-name collisions, or deeply buried adversarial text as PHI. These are
the reason the production path still needs the prior OpenMed + regex stack, not rules alone.

## 1,132-Case Summary By Destination

### ChatGPT

- Rows: 1,132
- Expected PHI terms: 2,526
- Leaked expected PHI terms: 1,067
- Rows with at least one leak: 482
- Rows with a leak but `risk: low` and copy allowed: 482
- Average local runtime per row: 0.066 ms
- p95 local runtime per row: 0.188 ms

Failure buckets:

| Bucket | Leak rows |
| --- | ---: |
| name or proper noun | 438 |
| organization or geography | 21 |
| numeric or record identifier | 20 |
| nickname or relative | 1 |
| multi-patient or sibling | 1 |
| Spanish name or relation | 1 |

Top categories:

| Category | Rows | PHI terms | Leaked terms | Leak rows |
| --- | ---: | ---: | ---: | ---: |
| `name` | 289 | 578 | 484 | 242 |
| `amboss_r4_golden` | 60 | 514 | 189 | 58 |
| `dense_multi_phi` | 99 | 598 | 176 | 77 |
| `amboss_r4_validation` | 35 | 307 | 106 | 35 |
| `ssn` | 37 | 37 | 19 | 19 |
| `address` | 47 | 77 | 18 | 18 |

### Web Search

- Rows: 1,132
- Expected PHI terms: 2,526
- Leaked expected PHI terms: 915
- Rows with at least one leak: 409
- Rows with a leak but `risk: low` and copy allowed: 409
- Average local runtime per row: 0.061 ms
- p95 local runtime per row: 0.187 ms

Failure buckets:

| Bucket | Leak rows |
| --- | ---: |
| name or proper noun | 367 |
| numeric or record identifier | 20 |
| organization or geography | 19 |
| nickname or relative | 1 |
| multi-patient or sibling | 1 |
| Spanish name or relation | 1 |

Top categories:

| Category | Rows | PHI terms | Leaked terms | Leak rows |
| --- | ---: | ---: | ---: | ---: |
| `name` | 289 | 578 | 422 | 211 |
| `amboss_r4_golden` | 60 | 514 | 173 | 51 |
| `dense_multi_phi` | 99 | 598 | 122 | 50 |
| `amboss_r4_validation` | 35 | 307 | 98 | 31 |
| `ssn` | 37 | 37 | 19 | 19 |
| `address` | 47 | 77 | 18 | 18 |

## Common Failure Modes

### 1. Ordinary First/Last Names

The current local pattern catches names only in a few contextual shapes. Many ordinary clinician
snippets leak plain names:

```text
Pt Mary-Ann Jones, 35M on lisinopril 20mg, BP 138/85, titrate?
```

Copied prompt leaked `Mary-Ann` and `Jones`, removed nothing, and reported `risk: low`.

Representative failures:

- `Mary-Ann Jones`
- `Yael Lopez`
- `Maria Wilson`
- `Mohammed Jones`
- `James Jones`
- `Jiang MacDonald`

### 2. Dense Multi-PHI Leaves Names And City Fragments

Example:

```text
Family of Lisa Park (DOB 1950-08-01, MRN AB728038, lives at 5957 Cedar Ln,
Minneapolis) wants advice on dad's CHF management.
```

Copied prompt:

```text
Family of Lisa Park (75-year-old, [MRN], lives at [ADDRESS], Minneapolis)
wants advice on dad's CHF management.
```

Leaks: `Lisa`, `Park`, `Minneapolis`.

The street address and MRN were caught, but name and city-only geography survived.

### 3. Undashed SSNs

Dashed SSNs are covered. Undashed SSNs are not.

Example:

```text
SSN 520797012 on file, prior auth for tirzepatide?
```

Copied prompt leaked `520797012`, removed nothing, and reported `risk: low`.

### 4. City/State Geography Without ZIP

The location regex catches city/state/ZIP. It misses city/state without ZIP:

```text
Pt from San Diego, OH - TB screening required?
Pt from Boston, MA - TB screening required?
Pt from Fairview, CO - TB screening required?
```

These all stayed copyable as low risk.

### 5. Nicknames And Relative Names

Example:

```text
Lil D (that's what grandma Shirley calls him) has had 3 ear infections in 4 months,
he's 18 months - tubes criteria?
```

Leaks: `Lil D`, `Shirley`, `grandma`.

### 6. Multi-Patient/Sibling Queries

Example:

```text
Seeing siblings today - Emma (8yo) needs ADHD med check, her brother Noah (13mo)
needs MMR.
```

Leaks: `Emma`, `Noah`.

### 7. Spanish Relationship/Name Phrases

Example:

```text
La mama de Sofia dice que tiene fiebre hace 5 dias con ojos rojos - Kawasaki?
```

Leaks: `Sofia`, `mama`.

### 8. Organization, Practice, And Small-Town Context

Example:

```text
Only case of Wilson disease we've ever seen at Lakes Pediatrics in Monticello -
7 year old with KF rings and elevated LFTs, what's the full workup?
```

Leaks: `Lakes Pediatrics`, `Monticello`, `only case`.

This is a contextual identifier problem, not just a direct-name problem.

## Interpretation

The baseline run confirmed the previous skeptical physician red-team finding at larger scale: the
small app-local prototype had a false-confidence problem. It was fast and local, but allowed copy
when basic expected PHI terms remained in the copied prompt.

The post-patch run fixes the obvious regression against the two synthetic 500-query suites by
bringing the learned deterministic layer forward. It does not make the current local rules sufficient
for clinician pilot use by themselves. The prior 500/1,132 result files remain highly relevant
because they evaluated the stronger OpenMed + regex stack. The current web app still needs:

1. integration of the OpenMed + regex pipeline as the default decon engine, and
2. a stricter residual scanner over `safe_context`, `safe_query`, and `destination_prompt` before
   copy/open is allowed on adversarial or deeply contextual cases.

## Immediate Fix Order

1. Wire OpenMed SuperClinical 434M + regex as the default local engine.
2. Add second-pass residual scanner over `safe_context`, `safe_query`, and `destination_prompt`.
3. Block copy/open when residual expected direct identifier patterns remain.
4. Add CLI batch runner so this 1,132-case suite runs before every release.
5. Decide and document the product policy for exact age and medication dose retention, because the
   Amboss fixture treats some clinically useful values as PHI while the product currently preserves
   exact age when it is useful.

## Reproduction Command

The batch was run locally with an ad hoc Python harness using:

```bash
PYTHONPATH=package/src python3 <local batch script>
```

The harness called:

```python
decontextualize_text(query, destination=destination, reference_date=date(2026, 6, 15))
```

and compared `result.destination_prompt` against each fixture row's `phi` terms.

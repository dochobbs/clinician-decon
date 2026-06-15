# Headless Validation Runbook

Date: 2026-06-15

This runbook explains how to validate Clinician Decon from a terminal or CI system after cloning
the repo. It is designed for contributors, partner evaluators, and release checks.

## Quick Start From A Fresh Clone

```bash
cd clinician-decon
python3 package/scripts/run_validation.py
```

Expected current result:

```text
Decon validation PASS
Suites: usability, adversarial
Destinations: chatgpt, gemini, web_search
Source cases: 1000
Outputs: 3000
PHI leaked outputs: 0
Unsafe copy-allowed leaks: 0
Clinical labeled outputs: 3000
Clinically usable outputs: 3000
Clinical usability rate: 100.00%
Handoff usability rate: 100.00%
```

This default command runs the current release gate:

- `package/data/decon_usability_500_2026-06-15.json`
- `package/data/decon_adversarial_500_2026-06-15.json`

It checks both safety and usefulness:

- expected PHI must not survive in copied output
- required clinical facts must remain present
- copy must not be allowed when a PHI leak is detected

## Installable Command

After installing the package:

```bash
cd package
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
decon-validate
```

The package command and source-checkout wrapper call the same code path.

## CI Command

Recommended PR gate:

```bash
python3 -m pytest package/tests
python3 package/scripts/run_validation.py --report package/reports/latest-validation.json
```

The command exits with:

- `0` when all selected gates pass
- `1` when PHI leaks, unsafe copy-allowed leaks, or clinical-usability threshold misses occur

## Common Commands

Run only the current safety + usability gate:

```bash
python3 package/scripts/run_validation.py --suite current
```

Run one destination:

```bash
python3 package/scripts/run_validation.py --suite current --destinations chatgpt
```

Write a JSON report:

```bash
python3 package/scripts/run_validation.py \
  --suite current \
  --report package/reports/latest-validation.json
```

Print the full JSON payload:

```bash
python3 package/scripts/run_validation.py --json-only
```

Explore legacy PHI-only fixtures without failing on known legacy label conflicts:

```bash
python3 package/scripts/run_validation.py --suite legacy-phi --allow-phi-leaks
```

Run a stricter or looser clinical-use threshold:

```bash
python3 package/scripts/run_validation.py --min-clinical-usable 0.99
```

## Suites

| Suite | Kind | Default gate | Purpose |
| --- | --- | --- | --- |
| `current` | alias | yes | Runs `usability` plus `adversarial`. |
| `usability` | clinical-usability | yes | Confirms clinically necessary facts survive decon. |
| `adversarial` | clinical-usability | yes | Probes hard PHI and prompt-shape failures. |
| `legacy-phi` | alias | no | Runs older copied PHI-only suites except the combined duplicate. |
| `legacy-synth-500` | PHI-only | no | Broad synthetic PHI coverage from prior work. |
| `legacy-synth-500-b` | PHI-only | no | Second broad synthetic draw from prior work. |
| `legacy-amboss-stress` | PHI-only | no | Older Amboss stress labels; includes clinical facts labeled as PHI-like. |
| `legacy-combined-1132` | PHI-only | no | Combined legacy corpus for exploration and trend comparison. |
| `all` | alias | no | Current gate plus the non-combined legacy PHI suites. |

## Thresholds

The current release gate should use:

```bash
python3 package/scripts/run_validation.py \
  --suite current \
  --min-clinical-usable 1.0
```

This means:

- any detected PHI leak fails the gate
- any unsafe copy-allowed leak fails the gate
- any missing required clinical fact in current labeled suites fails the gate

For exploratory model or rules work, use a lower clinical threshold only when the goal is to
compare branches. Do not use a lower threshold as a release gate without documenting why.

## Report Shape

The JSON report contains:

- `summary`: aggregate counts and rates
- `suite_results`: per-suite summary and representative failures
- `failure_reasons`: release-gate failure messages
- `passed`: Boolean gate outcome

Important fields:

- `source_cases`: number of source inputs
- `outputs`: source cases multiplied by selected destinations
- `clinical_labeled_outputs`: outputs with required clinical facts
- `phi_leaked_outputs`: outputs where expected PHI survived
- `unsafe_copy_allowed_outputs`: PHI-leaking outputs where copy was still allowed
- `missing_critical_fact_outputs`: outputs where required clinical facts were missing
- `clinical_usable_rate`: required facts retained among clinically labeled outputs
- `handoff_usable_rate`: PHI-safe, clinically usable, and copy-allowed among clinically labeled outputs

## What This Does Not Prove

The current default gate validates the shipped synthetic/adversarial distribution. It does not
prove universal PHI safety across real clinical notes.

Use the current gate to prevent regressions. Use clinician-reviewed gold traces to strengthen
external validation claims.

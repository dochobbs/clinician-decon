# decon

Python package and local web prototype for clinician-facing PHI minimization.

The package can run as a local web app, CLI, or library. The packaged Mac app wraps the local web
UI in a native window. The current app path is fully local: deterministic rules plus OpenMed local
PHI-NER as the default user-facing engine.

## Decon Vs De-ID

Traditional de-identification removes or masks identifiers from a note. Clinician Decon is more
task-specific: it removes identifiers and risky context while preserving the clinical facts needed
for a useful AI or search prompt.

Examples:

| Input contains | Decon output should preserve |
| --- | --- |
| `DOB 3/15/2013` | clinical age band, such as `adolescent` |
| `A1c 8.2` | `elevated A1c` when exact value is not needed |
| `28 kg, epinephrine autoinjector dose?` | exact weight when needed for dosing |
| `Addison Brooks has Addison disease` | diagnosis preserved, patient name removed |
| `Only HLH patient on 7th floor today` | `Rare HLH case`, floor/date removed |

## What Is Here

- `src/decon/local_rules.py`: deterministic decon, engine routing, and residual risk checks.
- `src/decon/openmed_ner.py`: optional OpenMed local PHI-NER span detector.
- `src/decon/setup_openmed.py`: setup command for local OpenMed model files.
- `src/decon/model_setup.py`: local model/runtime readiness checks.
- `src/decon/app_server.py`: standard-library HTTP server for the local prototype.
- `web/`: static local web interface.
- `src/decon/destinations.py`: external LLM, external search, and copy-only handoff definitions.
- `tests/`: regression tests for rules, destination handoff, setup status, validation, and service
  behavior.
- `docs/`: research notes and clinician-facing tool brief.

## Install

```bash
cd package
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

No API key is needed for the local web app.

To run the model-backed engine, install optional OpenMed dependencies and download the model into
the local cache:

```bash
pip install -e '.[openmed]'
decon-setup-openmed
```

The OpenMed model files are not tracked in git. For repository-local development,
`decon-setup-openmed --repo-local` writes to `local-models/`, which is intentionally ignored by
git. The model used by this package is
[OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1](https://huggingface.co/OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1).

Without OpenMed setup, the app and CLI report the missing model as high risk and block copy by
default. Use `--engine local-rules` only for explicit deterministic-rule development or regression
testing.

## Run The Local App

```bash
PYTHONPATH=src python -m decon.app_server
```

Then open:

```text
http://127.0.0.1:8769
```

The app lets a clinician paste PHI-containing text, review the cleaned result, copy the safe
prompt, and open an external destination. Prompt text is never placed in the destination URL.

## Examples

### Vaccine Question

Input:

```text
Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today.
Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age.
```

Safe review context:

```text
[NAME] adolescent [MRN] came in same-day. parent called from [PHONE] asking what vaccines he needs at this age.
```

Search prompt:

```text
adolescent immunization schedule vaccines current guidelines
```

### Medication Question

Input:

```text
Patient Lia Chen DOB 9/5/2025 has fever 102.1 and decreased intake.
Parent asks when an infant needs urgent evaluation.
```

Safe prompt:

```text
Patient [NAME] infant 6-11 months has fever 102.1 and decreased intake.
Parent asks when an infant needs urgent evaluation.
```

### Eponym Collision

Input:

```text
Referral for Addison Brooks. Addison disease on fludrocortisone, vomiting; stress-dose steroid?
```

Safe prompt:

```text
Referral for [NAME]. Addison disease on fludrocortisone, vomiting; stress-dose steroid?
```

## CLI

```bash
decon "Marcus Johnson, DOB 3/15/2013, needs vaccine guidance"
```

Use a destination template:

```bash
decon "Marcus Johnson, DOB 3/15/2013, needs vaccine guidance" --destination web_search
```

Use stdin and JSON output in a pipeline:

```bash
printf '%s\n' "Parent asks about guanfacine for Jordan before camp July 12" | decon --json
```

The CLI is fully local and useful for quick experiments. The browser app and `decon-validate`
command are the preferred paths for release validation.

## Test

```bash
PYTHONPATH=src python -m pytest
```

Current local snapshot:

```text
140 passed
```

## Headless Validation

From a source checkout:

```bash
PYTHONPATH=package/src /path/to/python-with-transformers \
  package/scripts/run_validation.py --engine rules+openmed
```

After package install:

```bash
decon-validate --engine rules+openmed
```

Current default gate summary:

```text
Source cases: 1050
Outputs: 3150
PHI leaked outputs: 0
Unsafe copy-allowed leaks: 0
Clinical labeled outputs: 3150
Clinically usable outputs: 3150
Clinical usability rate: 100.00%
Handoff usability rate: 100.00%
Max avg runtime: 100.098 ms
Max p95 runtime: 123.279 ms
```

Run the larger persona-driven regression gate:

```bash
python3 package/scripts/run_validation.py --suite persona-regression --engine rules+openmed
```

Generate the checked-in persona regression suite:

```bash
python3 package/scripts/generate_traces.py \
  --count 2000 \
  --seed 20260615 \
  --output package/data/decon_persona_regression_2000_2026-06-15.json \
  --report package/reports/persona-regression-2000-2026-06-15.json
```

Write a JSON report for CI:

```bash
python3 package/scripts/run_validation.py \
  --suite current \
  --engine rules+openmed \
  --report package/reports/latest-validation.json
```

See:

- `../docs/qa/headless-validation.md`
- `../docs/qa/synthetic-trace-generation.md`
- `../docs/qa/persona-library.md`
- `../docs/install/mac-clean-install.md`
- `../docs/qa/mac-installer-qa.md`

## Mac Installer

The doctor-facing Mac artifact is the self-contained DMG:

```bash
../installer/mac/build_self_contained_dmg.sh
```

Expected Apple Silicon output:

```text
../dist/mac/Clinician-Decon-0.1.0-self-contained-arm64.dmg
```

The smaller bootstrap DMG remains available for development and troubleshooting, but it is not the
clinician install path.

## Safety Notes

- The local app processes text on `127.0.0.1`.
- The model-backed engine loads local files only during decon.
- Names, MRNs, phone numbers, email, SSNs, URLs, street addresses, and ZIP-level geography are
  removed or replaced.
- DOB and exact ages are converted to clinical age bands when parseable.
- Relative/caregiver names are removed while broad relationship context can remain.
- Clinical values may be generalized when exact values are not necessary.
- This is a PHI minimization prototype, not a legal or compliance guarantee.

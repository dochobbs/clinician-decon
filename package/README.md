# decon

Python package and local web prototype for clinician-facing PHI minimization.

The package can run as a local browser app, CLI, or library. The current app path is fully local
and rules-based. Older model-backed code and evaluation fixtures are still present so we can
compare local rules, local NER, and cloud or BAA-covered rewrite approaches.

## What Is Here

- `src/decon/local_rules.py`: local deterministic decon engine used by the web app.
- `src/decon/app_server.py`: stdlib HTTP server for the local prototype.
- `web/`: static PWA-style interface.
- `src/decon/destinations.py`: ChatGPT, Gemini, Claude, OpenEvidence, Web Search, and Copy Only
  copy/open handoff definitions.
- `src/decon/pipeline.py`, `service.py`, `tasks.py`: older task-mode and model-backed pipeline.
- `tests/`: regression tests for decon rules, destination handoff, setup status, validation, and
  service behavior.
- `docs/`: copied research notes, partner notes, and clinician tool brief.

## Install

```bash
cd /Users/dochobbs/Downloads/Consult/clinician-decon/package
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

No API key is needed for the local web app.

## Run the Local App

```bash
PYTHONPATH=src python -m decon.app_server
```

Then open:

```text
http://127.0.0.1:8769
```

The app lets a clinician paste PHI-containing text, review the cleaned result, copy the safe
prompt, and open a third-party destination. Prompt text is never placed in the destination URL.

## Example

Input:

```text
Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today.
Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age.
```

Web Search output:

```text
13-year-old pediatric immunization schedule vaccines current guidelines
```

Review context:

```text
[NAME] 13-year-old [MRN] came in same-day. parent called from [PHONE] asking what vaccines he needs at this age.
```

## CLI

The package still includes the original CLI:

```bash
decon "Marcus Johnson, DOB 3/15/2013, needs his 13-year-old vaccines per AAP"
```

Set `ANTHROPIC_API_KEY` only when running the older live model-backed decontextualizer path.

## Test

```bash
PYTHONPATH=src python -m pytest
```

Current local snapshot:

```text
94 passed
```

## Headless Validation

From a source checkout:

```bash
cd /Users/dochobbs/Downloads/Consult/clinician-decon
python3 package/scripts/run_validation.py
```

After package install:

```bash
decon-validate
```

Current default gate:

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
```

Run the larger persona-driven regression gate:

```bash
python3 package/scripts/run_validation.py --suite persona-regression
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
  --report package/reports/latest-validation.json
```

See `../docs/qa/headless-validation.md` for the full runbook,
`../docs/qa/synthetic-trace-generation.md` for the trace-generation strategy, and
`../docs/qa/persona-library.md` for the versioned synthetic persona vocabulary.

Run the local usability suite:

```bash
python scripts/run_usability_eval.py
```

This generates `package/data/decon_usability_500_2026-06-15.json`,
`package/reports/local-usability-500-2026-06-15.json`, and
`docs/qa/2026-06-15-local-usability-500-eval.md`.

## Safety Notes

- The local app processes text on `127.0.0.1`.
- Names, MRNs, phone numbers, email, SSNs, URLs, street addresses, and ZIP-level geography are
  removed or replaced.
- DOB is converted to age when parseable; ages over 89 are aggregated to `90 or older`.
- Relative/caregiver names are removed while broad relationship context can remain.
- Clinical values may be generalized when exact values are not necessary, for example `A1c 8.2`
  to `elevated A1c`; exact weight or severe lab values are preserved when needed for dosing or
  criteria checks.
- This is a PHI minimization prototype, not a legal or compliance guarantee.

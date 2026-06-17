# Clinician Decon

Clinician Decon is a local-first tool for turning PHI-containing clinical text into a
reviewable, paste-ready prompt for external AI or search tools.

The core workflow is simple:

1. Paste clinical text from a protected workflow.
2. Run decontextualization locally on your machine.
3. Review what was removed or generalized.
4. Copy the safe prompt, then paste it into the destination yourself.

Raw pasted text is processed on `127.0.0.1`. The app does not put prompt text in third-party URLs.

## Decon Vs De-ID

Traditional de-identification tries to remove or mask identifiers from a document. That is useful
for releasing notes or datasets, but it can make a prompt less useful because it often replaces
clinical context with blanks or asterisks.

Decontextualization is stricter about the handoff task: remove direct identifiers and risky
context, but preserve the clinical facts needed for a useful answer.

Examples:

| Input contains | Traditional de-ID might do | Clinician Decon aims to do |
| --- | --- | --- |
| `DOB 3/15/2013` | mask the date | convert to `adolescent` |
| `A1c 8.2 and BMI 31` | leave exact values or mask them | convert to `elevated A1c` and `obesity-range BMI` when exact values are not needed |
| `Addison Brooks has Addison disease` | mask both `Addison` terms | remove the patient name, preserve `Addison disease` |
| `Only HLH patient on 7th floor today` | may leave uniqueness context | convert to `Rare HLH case` and remove floor/date identifiers |
| `MRN LP-2024-08432` | mask with asterisks | replace with `[MRN]` and record only the removed category |

The goal is not to prove a document is legally de-identified. The goal is to help a clinician
create a safer, clinically useful prompt before using tools that should not receive raw PHI.

## What It Does

Clinician Decon removes or generalizes common identifiers and risky context:

- names, relatives' names, nicknames, and provider names
- MRNs, chart IDs, accession IDs, claim IDs, serials, QR payloads, and similar identifiers
- phone numbers, emails, URLs, IP addresses, and device/network identifiers
- street addresses, ZIP-level geography, schools, camps, facilities, rooms, units, beds, and floors
- exact dates, relative dates, exact ages, and birth dates
- prompt-injection text such as instructions to preserve identifiers

It preserves clinical usefulness where possible:

- DOB and exact ages become clinical age bands.
- severe or decision-relevant labs can remain when needed for triage or criteria.
- exact weights can remain when needed for weight-based dosing.
- broad relationship context can remain, such as `parent reports patient`.
- clinical eponyms and diagnoses are preserved when they are not patient identifiers.

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

### Medication Side Effect

Input:

```text
Marvin stopped methylphenidate 2 days ago because anxiety worsened.
Mother Jennifer asks whether guanfacine 1 mg every morning is reasonable before camp July 12.
```

Safe prompt:

```text
Patient stopped methylphenidate 2 days ago because anxiety worsened.
Parent asks whether guanfacine 1 mg every morning is reasonable before camp [DATE].
```

### Clinical Eponym Collision

Input:

```text
Referral for Addison Brooks. Addison disease on fludrocortisone, vomiting; stress-dose steroid?
```

Safe prompt:

```text
Referral for [NAME]. Addison disease on fludrocortisone, vomiting; stress-dose steroid?
```

### Not Enough Clinical Content

Input:

```text
pt reports saw Dr. Thomas on 4/12/26
```

Safe review context:

```text
pt reports saw Dr. [NAME] on [DATE]
```

This is safe, but it is not a useful clinical question. The reviewer should add a de-identified
clinical question before sending it anywhere.

## Current App

The runnable package lives in `package/`.

```bash
cd package
PYTHONPATH=src python -m decon.app_server
```

Open:

```text
http://127.0.0.1:8769
```

Current behavior:

- deterministic local rules plus OpenMed local PHI-NER as the default user-facing engine
- browser-based paste, decon, review, copy, and open workflow
- destination options for external LLMs, external search, and copy-only handoff
- no prompt text embedded in third-party URLs
- setup/model status endpoint that verifies repo-local model files and Python runtime support
- copy is blocked when the OpenMed-backed engine is requested but unavailable

## OpenMed Work Used

The optional model-backed engine uses OpenMed's published PHI/PII token-classification model as a
second detector after deterministic local rules:

- Model: [OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1](https://huggingface.co/OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1)
- Publisher page: [OpenMed on Hugging Face](https://huggingface.co/OpenMed)
- Local integration: [`package/src/decon/openmed_ner.py`](package/src/decon/openmed_ner.py)
- Setup command: `decon-setup-openmed`

The model files are not tracked in this git repo. Setup downloads or copies them into a local model
cache, and decontextualization loads them with `local_files_only=True`. For repository-local
development, `decon-setup-openmed --repo-local` installs the files under `package/local-models/`,
which is ignored by git.

The local-rules engine remains available for deterministic regression work, but it is not the
release safety posture. The web app, CLI, and `decon-validate` command default to `rules+openmed`;
if OpenMed is missing, they fail closed or block copy instead of reporting a low-risk handoff.

The OpenMed model page lists the model license as Apache-2.0. That license applies to the model
asset separately from this project's license.

## Install For Local Development

```bash
cd package
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

No API key is needed for the local web app.

To run the OpenMed-backed local PHI-NER engine, install optional runtime dependencies and download
the model into the local cache:

```bash
pip install -e '.[openmed]'
decon-setup-openmed
```

The default model target is the per-user Decon app-data directory. For repository-local development,
use:

```bash
decon-setup-openmed --repo-local
```

That writes to `package/local-models/OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1/`, which is
ignored by git.

Without OpenMed setup, the user-facing app and CLI still run local rules, but they report the
missing model as high risk and block copy by default. Use `--engine local-rules` only for explicit
rule-development or regression testing.

## Validation

Run unit tests:

```bash
cd package
PYTHONPATH=src python -m pytest
```

Current local snapshot:

```text
134 passed
```

Run the model-backed headless validation gate:

```bash
PYTHONPATH=package/src /path/to/python-with-transformers \
  package/scripts/run_validation.py --engine rules+openmed
```

Current validation snapshot:

```text
1,050 source cases, 3,150 destination outputs, 0 PHI leaks, 0 missing clinical facts,
100% handoff usable, max avg runtime 100.098 ms, max p95 runtime 123.279 ms
```

Additional useful gates:

```bash
python3 package/scripts/run_validation.py --suite clinician-seed-gold --engine rules+openmed
python3 package/scripts/run_validation.py --suite persona-regression --engine rules+openmed
python3 package/scripts/run_validation.py --suite phi-field-prose --engine rules+openmed
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam --engine rules+openmed
python3 package/scripts/run_validation.py --suite validation-blindspot-redteam-r2 --engine rules+openmed
```

## Important Docs

- [Repository map](SOURCE_MAP.md)
- [Headless validation runbook](docs/qa/headless-validation.md)
- [Decon query set registry](docs/qa/query-set-registry.md)
- [Synthetic trace generation strategy](docs/qa/synthetic-trace-generation.md)
- [Synthetic persona library](docs/qa/persona-library.md)
- [Local rules and model-backed pipeline audit](docs/qa/2026-06-16-local-rules-openmed-audit.md)
- [External de-ID baseline head-to-head](docs/qa/2026-06-16-external-deid-baseline-head-to-head.md)
- [External de-ID baseline error samples](docs/qa/2026-06-16-external-deid-baseline-error-samples.md)
- [External de-ID adversarial add-on](docs/qa/2026-06-16-external-deid-adversarial-addon-head-to-head.md)
- [Mac installer implementation plan](docs/superpowers/plans/2026-06-15-mac-installer-implementation-plan.md)
- [Clinician tool brief](package/docs/clinician-decon-tool-brief.md)

## Directory Layout

```text
clinician-decon/
  README.md
  SOURCE_MAP.md
  package/
    Python package, local server, web UI, tests, fixtures, and scripts.
  docs/
    QA reports, design notes, installer planning, and validation runbooks.
```

## Current Recommendation

Use `package/` as the release seed:

1. Keep deterministic rules as the first pass.
2. Keep the local PHI-NER model as the second pass when installed.
3. Keep residual-risk scanning after both layers.
4. Fail closed when the model-backed engine is explicitly requested but unavailable.
5. Use the checked-in synthetic and adversarial suites as regression gates before packaging.

## Safety Notes

- This is a PHI-minimization prototype, not a legal or compliance guarantee.
- Raw pasted text should stay local to the app runtime.
- The user must review the cleaned prompt before copying it into any external tool.
- Validation suites are synthetic and adversarial; they do not prove universal safety across real
  clinical notes.

## License

This project is licensed under the [Fair License](LICENSE). Third-party model files and other
external assets remain under their own licenses.

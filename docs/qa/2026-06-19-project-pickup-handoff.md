# Project Pickup Handoff

> Superseded for current hybrid-pipeline work by
> `docs/qa/2026-09-09-hybrid-decon-hardening-handoff.md`.

Date: 2026-06-19

Repo: `clinician-decon`

Branch: `main`

State captured after commit `61d8ecf chore: prune generated report artifacts`.

## Current State

Clinician Decon is a local-first decontextualization tool for turning PHI-contaminated clinical
text into a safer prompt for external LLM or search use. The working production-shaped path is:

```text
deterministic regex/rules
  -> local model-backed PHI NER
  -> deterministic post-normalization
  -> residual risk scan
  -> destination handoff
```

The model-backed engine is the intended validation/release path. Rules-only remains useful for
tests and deterministic pre/post filtering, but should not be treated as the full safety engine.

The repository is pushed and clean. Build artifacts, DMGs, local model files, local agent state,
generated report JSON, and historical raw result JSON are ignored.

## What Changed Recently

Hardening work:

- Added `package/data/decon_realworld_adversarial_24_2026-06-19.json`.
- Registered it as `realworld-adversarial` in the validation runner.
- Added generalized rules for:
  - EHR/export wrapper cleanup.
  - `Sex: Male/Female` -> broad sex context.
  - HL7-style pipe message normalization.
  - `tomorrow` -> `next day`.
  - bare local portal URLs.
  - generic named pharmacy locations.
- Added regression tests for the above.
- Scrubbed the new adversarial suite and QA doc to avoid real PHI and avoidable third-party
  example names.

Repo hygiene:

- Removed generated JSON reports from git:
  - `package/reports/*.json`
  - `historical-fixtures/**/results/**/*.json`
- Added `package/reports/README.md`.
- Added `historical-fixtures/workbench/results/README.md`.
- Added `.gitignore` rules for generated reports, local model files, local build output,
  `.claude/`, and `.remember/`.

Mac installer work:

- Keep the Mac installer source in git:
  - `installer/mac/*.sh`
  - `installer/mac/native/ClinicianDeconApp.swift`
  - `installer/mac/app/*.plist`
  - `installer/mac/app/clinician-decon-launcher`
  - `installer/mac/assets/decon-mark.svg`
  - `installer/mac/assets/ClinicianDecon.icns`
  - `docs/install/*.md`
- Do not commit built `.app` bundles, DMGs, `build/`, `dist/`, generated iconsets, or local model
  files.

## Validation Evidence

Most recent focused test after report pruning:

```bash
python3 -m pytest \
  package/tests/test_validation_runner.py \
  package/tests/test_persona_trace_generator.py \
  package/tests/test_validate.py \
  -q
```

Result: `30 passed`.

Most recent full package test before report pruning:

```bash
python3 -m pytest package/tests -q
```

Result: `149 passed`.

Most recent focused model-backed real-world adversarial validation:

- Suite: `realworld-adversarial`
- Source cases: `24`
- Outputs: `72`
- PHI leaked outputs: `0`
- Unsafe copy-allowed leaks: `0`
- Missing critical fact outputs: `0`
- Clinical usability rate: `100.00%`
- Handoff usability rate: `100.00%`

Most recent expanded model-backed regression:

- Suites: `current`, `phi-field-prose`, `validation-blindspot-redteam`,
  `validation-blindspot-redteam-r2`, `clinician-seed-gold`, `realworld-adversarial`
- Source cases: `1,151`
- Outputs: `3,453`
- PHI leaked outputs: `0`
- Unsafe copy-allowed leaks: `0`
- Missing critical fact outputs: `0`
- Clinical usability rate: `100.00%`
- Handoff usability rate: `100.00%`

Raw JSON reports were intentionally not committed. The durable summaries live in `docs/qa/`.

## Important Docs

- `README.md`: project overview.
- `package/README.md`: CLI, validation, and local package workflow.
- `docs/install/mac-clean-install.md`: clinician-facing Mac install path.
- `docs/install/mac-package-audit.md`: package transparency/audit note for the DMG.
- `docs/qa/headless-validation.md`: headless validation workflow.
- `docs/qa/query-set-registry.md`: current suite inventory.
- `docs/qa/2026-06-19-realworld-adversarial-hardening.md`: latest adversarial hardening trace.
- `docs/qa/2026-06-16-local-rules-openmed-audit.md`: model-backed pipeline audit.
- `docs/decon-vs-deid-explainer.md`: conceptual explanation.

## Rebuild And Validate

Run the normal package tests:

```bash
python3 -m pytest package/tests -q
```

Run the model-backed validation from a build with the bundled local model:

```bash
DECON_HOME="$PWD/build/live-decon-home" \
DECON_MODEL_DIR="$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/package/local-models/<local-model-dir>" \
PYTHONPATH="$PWD/package/src:$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python-packages" \
"$PWD/build/mac-self-contained/Clinician Decon.app/Contents/Resources/python/bin/python" \
  -m decon.validation_cli \
  --suite current \
  --suite phi-field-prose \
  --suite validation-blindspot-redteam \
  --suite validation-blindspot-redteam-r2 \
  --suite clinician-seed-gold \
  --suite realworld-adversarial \
  --destinations <configured-destinations> \
  --reference-date 2026-06-19 \
  --engine <model-backed-engine> \
  --report /private/tmp/regression-plus-realworld-2026-06-19-model.json
```

Build the self-contained Mac DMG:

```bash
installer/mac/build_self_contained_dmg.sh
```

Expected local artifact:

```text
dist/mac/Clinician-Decon-0.1.0-self-contained-arm64.dmg
```

## Known Boundaries

- The OpenMed model files are not in git. The build script copies them from the ignored
  repo-local model directory or another `DECON_MODEL_SOURCE`.
- Release claims should stay scoped to the model-backed pipeline and documented synthetic suites.
- The synthetic suites are useful for regression hardening, but they do not replace clinician
  review of real examples.
- Exact values are intentionally task-aware:
  - dosing weights can be preserved;
  - exact ages are generalized to age bands;
  - BMI/A1c are generalized when strict safe-prompt policy applies;
  - severe labs may be preserved or clinically summarized when needed for usability.

## Recommended Next Moves

1. Run a clean-install DMG smoke test from a separate macOS user account or separate Mac.
2. Do a 10-case clinician review pass using short, difficult synthetic examples and record
   accept/reject reasons in `docs/qa/`.
3. Rebuild the self-contained DMG after any UI/engine changes and update `docs/qa/mac-installer-qa.md`
   if behavior changes.
4. Decide whether the 2,000-case persona regression suite should remain checked in or be
   regenerated on demand. It is currently kept because it is a runnable regression gate.
5. For broader distribution, add Developer ID signing and notarization; the current demo build is
   not App Store/notarization ready.

## Git Hygiene Policy

Keep in git:

- source code,
- tests,
- validation suite inputs,
- docs and QA summaries,
- Mac installer source and small assets.

Do not commit:

- generated report JSON,
- built apps or DMGs,
- local model files,
- local logs,
- local agent state,
- Python/Swift build caches.

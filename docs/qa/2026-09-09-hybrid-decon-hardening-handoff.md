# Hybrid Decon Hardening Handoff

Date: 2026-09-09 (America/Chicago)

- Theme: `clinician-decon`
- Resume aliases: `clinician decon`, `decon`, `OpenMed regex hybrid`, `PPLX comparison`
- Status: complete for the current engineering iteration; paused at the independent-evidence boundary
- Canonical handoff: `/Users/dochobbs/consult/clinician-decon/docs/qa/2026-09-09-hybrid-decon-hardening-handoff.md`
- Best next move: build a blinded, clinician-reviewed validation set that is not used to write rules, then run it alongside the existing release gate

## Outcome and decision boundary

The production direction is the hybrid pipeline:

```text
deterministic structured-PHI rules
  -> OpenMed semantic PHI NER
  -> span precedence and composition
  -> clinical normalization and preservation
  -> residual-output scan and fail-closed copy gate
  -> destination rendering
```

In plain language: rules catch predictable formats, OpenMed catches PHI from meaning and context,
and the final scanner blocks copying when masking looks incomplete. Clinical-fact assertions stop
over-redaction from producing a false pass.

PPLX remains an experimental comparison arm. Its adapter, pinned provenance, comparison harness,
and evaluation findings are preserved, but it is not part of the production pipeline because the
broad local comparison found materially more clinical fact loss.

The current results support a strong synthetic regression boundary for represented cases. They do
not prove completeness on unseen real-world notes.

## What was built and learned

- Made deterministic whole-field spans authoritative over shorter model fragments.
- Added structured coverage for patient-record IDs, FHIR resource IDs, HL7 PID fields, JSON
  identifiers, OCR-spaced identifiers, repeated identifiers, multiple identifiers, and portal
  tokens.
- Propagated confidently introduced patient names, name parts, and portal-handle variants across
  conversation turns while preserving clinical eponyms such as Bell palsy and Kawasaki disease.
- Added residual checks for contiguous, split-placeholder, and OCR-spaced identifier remnants.
- Corrected the evaluator so exact-string disappearance alone cannot hide a partially retained ID,
  while generic field words such as `patient` do not create false-positive leaks.
- Added `conversation-repeat`, `structured-boundary`, `residual-identifier-redteam`, and
  `bare-name-shapes` to the release vocabulary.
- Preserved PPLX model-comparison code and evidence without adding its model weights or generated
  reports to Git.

## Repository and Git state

- Repository/worktree: `/Users/dochobbs/consult/clinician-decon`
- Branch: `main`
- Upstream: `origin/main`
- Implementation HEAD at closeout start: `0801fbb7dd1a9b06f16eb77b9982a0b09038f1fe`
- Upstream divergence at closeout start: `0 behind / 0 ahead`
- Working tree at closeout start: clean
- Task-owned base: `271fc08`
- Exact task range before this handoff: `271fc08..0801fbb`
- Range size: 32 files changed, 3,622 insertions, 23 deletions

Task-owned commits:

- `0f5220f FIX: complete partially detected full names`
- `9d53e7a DOCS: record bare full-name privacy fix`
- `0801fbb Harden hybrid decon pipeline and release gates`

The work was committed directly to `main` and pushed; there was no feature branch or pull request to
merge. No deployment was performed.

## Durable artifacts

- `README.md`: current hybrid architecture and release snapshot.
- `docs/qa/2026-09-02-pplx-pii-masking-openmed-head-to-head.md`: fair raw-model and product-pipeline comparison.
- `docs/qa/2026-09-02-residual-identifier-redteam.md`: evaluator correction and residual-ID before/after results.
- `docs/qa/query-set-registry.md`: release-suite inventory and latest results.
- `package/src/decon/span_composition.py`: model-span composition and clinical shielding.
- `package/src/decon/conversation_eval.py`: deterministic cross-turn generator.
- `package/src/decon/structured_boundary_eval.py`: adversarial structured identifiers plus matched clean controls.
- `package/src/decon/pplx_ner.py`: experimental PPLX adapter with pinned provenance checks.
- `package/scripts/compare_pii_models.py`: shared product-pipeline comparison harness.
- `package/scripts/smoke_installed_app.py`: installed-app API smoke gate.

Ignored local resources intentionally retained:

- repo-local OpenMed and PPLX model snapshots under `package/local-models/`;
- generated JSON evidence under `package/reports/`.

Neither resource class is tracked by Git.

## Verification

Full package suite:

```bash
PYTHONPATH=package/src \
  /Users/dochobbs/Downloads/Consult/cds-eval/.venv/bin/python \
  -m pytest package/tests -q
```

Result: `181 passed`, `9 warnings`, `806.53 seconds`. The warnings are dependency deprecations from
SWIG and Torch JIT; no test failed.

Closeout-focused regression over the generated suites, evaluator, release-alias registration, and
residual-ID gate: `13 passed`, `9 dependency warnings`, `12.01 seconds` on 2026-09-09.

Expanded cached-detector release evaluation:

- Source cases: `3,587`
- Destination outputs: `10,761`
- Detected PHI leaks: `0`
- Missing critical clinical facts: `0`
- Handoff usable: `10,761 / 10,761`

Production-style focused gate over the newly hardened suites:

- Source cases: `416`
- Destination outputs: `1,248`
- Detected PHI leaks: `0`
- Unsafe copy-allowed leaks: `0`
- Missing critical clinical facts: `0`
- Handoff usable: `1,248 / 1,248`

The raw OpenMed-only view remained materially weaker than the composed pipeline. The release result
therefore supports the hybrid as a unit, not OpenMed alone.

## Live and artifact state

- No process was listening on local Decon port `8769` at closeout.
- No current DMG was rebuilt, signed, notarized, deployed, or installed during this workstream.
- The source repository is verified; an existing packaged app must not be assumed to contain commit
  `0801fbb`.
- Before clinician use of a rebuilt app, run `package/scripts/smoke_installed_app.py` against its
  local server and record the artifact result separately.

## Unfinished and parked work

- A blinded clinician-reviewed evaluation set has not been created. The target recorded in the QA
  decision is at least 250 clean clinical conversations plus adversarial cases, multilingual
  paraphrases, and long-window boundaries.
- The green release evidence is predominantly synthetic and templated; prevalence and real-world
  generalization are not established.
- PPLX clinical calibration, especially for `other_pii`, is parked. Do not promote it into the
  production pipeline without a new blinded comparison that preserves the current clinical facts.
- The Mac artifact has not been rebuilt or live-smoke-tested with the hardened source.

## Resume

```bash
cd /Users/dochobbs/consult/clinician-decon
git fetch origin main
git status --short --branch
PYTHONPATH=package/src \
  /Users/dochobbs/Downloads/Consult/cds-eval/.venv/bin/python \
  -m decon.validation_cli --suite release --engine rules+openmed \
  --reference-date 2026-06-15
```

The model-backed commands require the existing ML-capable Python environment and local model
snapshots. Resume with: `pick up the clinician decon work` or `resume the OpenMed regex hybrid`.

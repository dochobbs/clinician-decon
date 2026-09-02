# Artifact smoke gate, bare-name suite, and eponym-location fix

**Date:** 2026-08-22

**Status:** implemented and validated locally

**Follows:** [Bare name span hardening](2026-08-22-bare-name-span-hardening.md)

## Incident: the live app was older than the validation

A Kestrel-side decon of the RWA-001 shape leaked the patient's first name in a note-body
parenthetical — `(Manning, 6th grade)` — with `risk_level: low` and `copy_allowed: true`.

Repository source was already clean: both `local-rules` and `rules+openmed` masked the name.
The server on port 8769 was the packaged self-contained app
(`build/mac-self-contained/Clinician Decon.app`), whose bundled `decon` snapshot predates the
June hardening commits. An HTTP probe against the live app returned the text fully unmasked.

Root cause of the escape: validation only ever ran against repository source. Nothing
re-tested a built artifact, so a stale bundle could serve leaks while every gate stayed green.

## Corrections

### 1. Artifact-level smoke gate

`package/scripts/smoke_installed_app.py` posts ten known-adversarial cases at a running
server's `/api/decon` endpoint and fails on any leaked forbidden term or lost required
clinical fact. Run against the repo server or a built app:

```bash
python3 package/scripts/smoke_installed_app.py --base-url http://127.0.0.1:8769
```

Against the stale live app it failed 4 of 10 cases (Manning recurrence, bare name with
clinical tail, all-caps name run, pre-K parenthetical) — exactly the fixes the bundle
predates. That failure is the gate working.

### 2. Bare-name shapes suite

`package/data/decon_bare_name_shapes_20_2026-08-22.json` registers 20 cases as the
`bare-name-shapes` suite: bare name runs with clinical tails, particle/hyphen/apostrophe
surnames, all-caps runs, parenthetical recurrences (the Manning class), plus anti-pattern
cases asserting clinical fragments (`chest pain`, `sore throat worse`, spelled-out ages)
survive. It passes with zero leaks under both `local-rules` and `rules+openmed`, so it gates
in pytest and in the release run.

Composition hardening that fell out of authoring it:

- expansion now stops at guarded clinical tails instead of refusing (`milo north fever`
  becomes `[NAME] fever` instead of leaking the surname),
- severity, laterality, body-part, and disease-class vocabulary joined the guard set,
- relation/provider lead-ins (`Mother Jennifer reports...`) are vetoed so caregiver context
  survives,
- the parenthetical school-stage tail accepts `pre-K`, kindergarten, and preschool in addition
  to numbered grades,
- a new deterministic rule masks capitalized bare name runs that cue patterns miss, so the
  rules layer covers the shape without the model.

### 3. Eponym mislabeled as location (pre-existing)

The expanded release gate exposed 20 persona-regression failures: OpenMed tags `Kawasaki` as
a location entity (it is also a Japanese city), and the clinical-eponym shield only inspected
`name`-category spans. Verified pre-existing by probing HEAD with the model available.

Fix: the shield now applies to every span category in `OpenMedSpanDetector`, and
`drop_clinical_eponym_spans` enforces the same guarantee at the composition boundary for any
span source. Context cues still protect real geography (`Wilson` without disease cues is kept).

### 4. Release gate alias

`--suite release` expands to every registered suite. New snapshot:

```text
3,171 source cases, 9,513 destination outputs, 0 PHI leaks, 0 unsafe copy-allowed leaks,
100% clinical usability, 100% handoff usability
```

## Verification

- Package suite: 167 passed.
- Release gate (rules+openmed, all ten suites): 9,513 outputs, 0 leaks, 100% usable.
- Smoke gate against stale live app: fails 4/10 as expected until the app is rebuilt.

## Process rules going forward

1. A built artifact must pass the smoke gate before being trusted, no matter how green the
   repository gates are.
2. New composition behavior needs both pattern and anti-pattern cases, in the gated suite,
   not only in unit tests.
3. Suites that are registered but never run under the real model are untested surface; the
   release alias exists so that cannot happen silently again.

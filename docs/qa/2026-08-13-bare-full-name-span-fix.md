# Bare full-name span correction

**Theme:** kestrel decon

**Status:** implemented, tested, committed locally, and verified live; not pushed or released

**Canonical handoff:** `/Users/dochobbs/Downloads/Consult/wren/.worktrees/kestrel-share-consult-2026-08-11/docs/sessions/2026-08-13-kestrel-local-build-closeout.md`

**Best next move:** review and push `0f5220f` plus this QA checkpoint, then rebuild and smoke-test the distributed Clinician Decon package before describing the fix as released.

## Incident

During Kestrel UI review, a lowercase bare two-token name was partially detected
by OpenMed. Full Decon replaced only the first token, left the surname visible,
and still returned `risk_level: low` plus `copy_allowed: true`. Kestrel correctly
consumed that approval and exposed the unsafe preview. The defect was in
Decon's model/rules composition boundary.

The example used to reproduce the defect was synthetic. No real patient data is
recorded here.

## Cause

- Local deterministic rules primarily recognized capitalized or clinically
  cued names, so the lowercase bare phrase did not produce a complete rule span.
- OpenMed marked only the first token.
- Decon accepted the model span as complete.
- Residual risk cannot safely classify every unknown lowercase word as a
  surname, so the remaining token was not blocked.
- Existing tests covered contextual and capitalized full names but not an
  intentionally partial model span over a lowercase, name-only input.

## Correction

Commit `0f5220f FIX: complete partially detected full names` changes
`package/src/decon/local_rules.py` and `package/tests/test_local_rules.py`.

When OpenMed returns a name span that overlaps an otherwise bare two-token
name-only input, deterministic composition replaces the entire phrase with one
name span. The expansion is deliberately restricted to the full input; a
clinical sentence such as a detected first name followed by `has asthma` keeps
the clinical text.

Kestrel was not given its own PHI regex. Decon remains the single approval
authority.

## Verification

- Focused local-rules tests: 78 passed.
- Complete package suite: 151 passed.
- Real local OpenMed probe for the failing shape returned exactly `[NAME]` with
  one span covering the full phrase.
- Real local OpenMed control removed the name and preserved `has asthma`.
- Kestrel's server-side Decon endpoint returned `[NAME]` after the corrected
  full service was restarted.

## Repository and live state

- Repo: `/Users/dochobbs/consult/clinician-decon`
- Branch: `main`
- Head before this note: `0f5220f`
- Upstream: `origin/main`; after this QA checkpoint is committed, local `main`
  is ahead by two commits: the code/test correction and this durable note.
- Pre-existing changes in `design-qa.md`,
  `docs/decon-vs-deid-explainer.md`, older QA files, and generated
  `package/src/decon.egg-info/` were not edited, staged, deleted, or included in
  the fix.
- Full Decon was running from the normal `main` checkout on port 8769 and passed
  a host-level model-backed API check at closeout.

## Prevention rule

Zero leaks in a validation corpus means zero observed leaks in that corpus. It
does not prove complete boundary handling. Model-backed PHI detectors need
explicit regression cases for partial entity spans and deterministic
composition behavior, including a preservation control for adjacent clinical
text.

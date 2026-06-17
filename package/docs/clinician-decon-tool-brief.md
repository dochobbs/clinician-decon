# Clinician Decon Tool Brief

**Date:** 2026-06-17
**Purpose:** Define the product shape for a dead-simple local tool that helps clinicians create
minimum-necessary, clinically useful prompts without sending raw PHI to external AI or search
destinations.

## Product Thesis

Clinicians often need help turning chart snippets, patient messages, labs, or visit context into a
question they can safely use elsewhere. Manual removal is error-prone: it can leave identifiers in
place, or it can strip so much context that the clinical question becomes useless.

Clinician Decon should become a copy-safe clinical context builder:

1. Paste or capture PHI-containing text from a protected source.
2. Run local PHI minimization before anything leaves the clinician's machine.
3. Show a clean, paste-ready prompt for the intended destination type.
4. Display what was removed by category, not by value.
5. Fail closed when the remaining text looks re-identifiable.

The product should be explicit that it is a risk-reduction and minimum-necessary tool, not a
guarantee of legal de-identification.

## Decon Vs De-ID

Classic de-identification is usually document-focused: remove or mask identifiers so a note or
dataset can be shared more safely.

Decontextualization is prompt-focused: remove identifiers, remove uniqueness context, and preserve
the clinical facts needed for the next task.

Examples:

- DOB becomes a clinical age band.
- exact age becomes a broader age band.
- exact lab values can become clinical signals when exact values are unnecessary.
- exact weights remain when needed for weight-based dosing.
- patient names are removed while clinical eponyms stay intact.
- room, floor, facility, school, camp, date, and "only patient" context is removed or generalized.

## Recommended Starting Shape

Build local-first before hosted.

- Local browser app served from loopback.
- Two-pane workflow: original text and safe prompt.
- Primary action: `Decontextualize`.
- Secondary actions: copy/open external destination, copy only, clear.
- Destination type selector:
  - external LLM
  - external search
  - copy only
- Risk chip:
  - `Low`: copy allowed.
  - `Medium`: copy allowed with warning and review.
  - `High`: copy blocked until edited or rerun.
- Audit panel:
  - removed categories only, never removed values.

## Baseline Pipeline

```text
paste text
  -> deterministic rules
  -> local PHI-NER model when installed
  -> residual risk scan
  -> destination-specific prompt/query shaping
  -> reviewed safe prompt
```

The default path must not send raw PHI to a cloud model. Any hosted or cloud rewrite mode should be
explicitly non-default and require the right contractual and policy review.

## What To Build First

### v0: Demo Worth Showing

- Web UI for paste -> decon -> review -> copy.
- Local deterministic rules.
- Optional local PHI-NER model.
- Canned examples from checked-in synthetic fixtures.
- Removed-category counts and risk chip.

Success bar: a clinician can understand and use it in under one minute.

### v1: Local-First Clinician Utility

- One-command local app.
- First-run setup checks for runtime, RAM, disk, and local model files.
- Explicit local-rules vs rules-plus-model engine status.
- Destination-specific prompt templates.
- Headless validation command for CI and local release checks.

Success bar: no cloud dependency for default decon and no raw prompt text persisted.

### v2: Workflow Integration

- Browser extension or native side panel.
- Context-menu action: `Sanitize selection`.
- Optional local native companion for model execution.
- Policy profiles by destination type.

Success bar: reduce risky copy/paste behavior inside the actual clinician workflow.

## UX Principles

- Default to local and fail closed.
- Make the user inspect the cleaned prompt.
- Show categories removed, never removed PHI values.
- Keep the screen dense and utilitarian.
- Make block reasons actionable:
  - likely MRN remains
  - full date remains
  - patient-specific URL remains
  - location or uniqueness context remains
  - no useful clinical question remains

## Compliance Framing

Recommended language:

> This tool helps minimize PHI before using external tools. It does not replace legal review,
> contractual coverage, institutional policy, or the clinician's responsibility to confirm that
> the remaining text is appropriate for the intended destination.

Avoid claiming that every output is legally de-identified.

## Evidence Base

The repo includes:

- unit tests for local rules, destinations, app server, setup status, and validation runner
- synthetic usability suites
- adversarial suites
- clinician seed-gold cases
- persona-driven generated traces
- an external de-ID baseline comparison

The current release gate is documented in `docs/qa/headless-validation.md`.

## Open Questions

- Should the first install target be a repo-based bootstrap script, a Mac app, or both?
- How strict should each destination profile be?
- Should the app block copying when the safe output is technically de-identified but clinically
  useless?
- What level of human-reviewed gold set is enough for the first pilot?

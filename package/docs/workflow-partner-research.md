# Workflow Partner Research

**Date:** 2026-06-17
**Goal:** Describe how Clinician Decon could integrate with a clinician workflow platform without
naming or evaluating any specific vendor.

## Bottom Line

A workflow platform is a strong integration target when it sits close to chart review, patient
messages, lab review, task management, evidence lookup, and AI-assisted drafting.

The integration should not imply that any partner is unsafe. The better framing is:

> Clinician Decon adds a visible minimum-necessary control layer whenever clinical context moves
> from a protected workflow into a less-protected or unknown destination.

## Strategic Fit

A good partner has:

- selected-text access or a browser-side workflow surface
- clinician-facing task or message workflows
- AI or evidence-search workflows that need patient context
- a trust story centered on privacy, auditability, and clinician control
- room for a local or client-side companion process

## Integration Concepts

### 1. Client-Side Sanitize Action

```text
Select text -> sanitize for AI -> review safe prompt -> copy/open destination
```

Why this is strong:

- simple clinician workflow
- no deep writeback required
- raw PHI can remain local
- user reviews the prompt before handoff

### 2. Minimum-Necessary Preprocessor

Run decon before any AI-assisted workflow receives chart context:

- destination-specific minimization policy
- category-level audit trail
- fail-closed risk gates
- no removed PHI values in logs

### 3. Evidence Query Builder

```text
patient context -> de-identified clinical question -> external evidence/search query
```

This is useful when the destination needs the clinical topic but does not need identity, exact
dates, room, facility, or local workflow context.

### 4. Safe External Prompt Card

Create a workflow card that produces a reviewed prompt for:

- clinical reasoning
- patient education draft
- evidence search
- referral summary
- care-plan summary

The destination type matters because minimization should be stricter for external destinations
than for covered internal flows.

## Suggested Pitch

Subject:

```text
Client-side PHI minimization for AI handoffs
```

Short pitch:

```text
Clinician Decon is a local-first decontextualization prototype that removes patient identifiers
and creates destination-specific, paste-ready clinical prompts before context is sent to external
AI or search tools.

The strongest integration is a "sanitize selected text" action: select chart, message, or lab
context; run local PHI minimization; review the cleaned prompt; then copy/open the destination.
It gives clinicians a one-click workflow while preserving minimum-necessary control, visible
review, and a local privacy boundary.
```

Proof points to attach:

- current headless validation gate
- synthetic and adversarial query-set registry
- external de-ID baseline comparison
- local-only app demo

## Risk And Positioning Notes

- Do not claim the tool makes arbitrary text safe.
- Do not imply a workflow partner currently exposes PHI unsafely.
- Use "minimum necessary", "destination-specific", "local-first", "visible controls", and
  "fail closed" language.
- Treat contractual coverage as destination-specific.
- If a hosted version handles raw PHI, require a clear legal and subprocessors review first.

## Diligence Questions

1. Where can selected text be accessed?
2. Can a local companion app receive selected text without server transit?
3. Which workflows most often lead to external copy/paste?
4. Is there a plugin, extension, or action surface?
5. Are AI destinations covered, external, or mixed?
6. Can removed-category metadata be stored without raw PHI?
7. What setup friction is acceptable for clinicians?

## Recommended Demo

- Local page with pasted synthetic chart/message/lab snippets.
- Output modes for external LLM, external search, and copy-only.
- Risk gate with category-level audit.
- Mock flow: select text -> sanitize -> review -> copy/open.

If a partner engages, propose a two-week technical spike:

- confirm integration surface
- run local decon on 50-100 synthetic workflow snippets
- compare local rules, rules plus model, and optional reviewer/fallback
- produce an integration plan and privacy review checklist

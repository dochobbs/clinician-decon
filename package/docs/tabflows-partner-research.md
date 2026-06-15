# Tabflows Partner Research

**Date:** 2026-06-15
**Goal:** Evaluate Tabflows as a partner, integration target, or pitch recipient for a
clinician-facing PHI minimization / decontextualization tool.

## Bottom Line

Tabflows is a strong fit for a decon pitch, but the pitch should be framed carefully.

They already position themselves as HIPAA-first, BAA-backed infrastructure for DPC workflows.
So the angle is not "Tabflows needs decon because it is unsafe." The better angle is:

> Tabflows can become the safest place for clinicians to move patient context between EHRs,
> AI assistants, evidence tools, scribes, messages, and tasks. Decon adds visible
> minimum-necessary controls and a local/client-side safety layer for any workflow that touches
> non-BAA or unknown-destination AI.

This is a partner/integration opportunity, not just a sales target.

## What Tabflows Is

Public positioning from Tabflows:

- "Your clinic, finally working as one."
- DPC-focused workflow layer that connects tools clinics already use.
- Core workflows include unified patient view, task management, team collaboration, draft
  assist, and Patient Assist.
- They list compatibility/integrations with Elation, Hint, Spruce, Quest, Cerbo, Fullscript,
  Atlas.md, Labcorp, ChartNote, OpenEvidence, Heidi, Freed, UpToDate, Rupa, Akute, and others.
- They emphasize that Core is free and Intelligence/Patient Assist scales with usage.
- Their trust page says they provide HIPAA documentation, encryption at rest and in transit,
  role-based access controls, and visible subprocessors.

Important implication: Tabflows is already very close to the clinician workflow where unsafe
copy/paste and AI handoff risk happens.

## Strategic Fit

### Why Tabflows Should Care

- Their product is about reducing tab switching and making context move between tools.
- Their AI surfaces need patient context to be useful.
- Their customers use evidence tools, scribes, patient messaging, EHRs, billing, labs, and
  likely general LLMs side by side.
- They already sell trust, BAA, and "your data stays yours."
- A decon layer can make their AI story sharper: not just HIPAA compliant, but
  minimum-necessary by design.

### Why We Should Care

- Tabflows has the exact distribution channel: DPC clinicians with fragmented tools.
- They support the right stack: Elation, Spruce, OpenEvidence, scribe tools, labs, and EHRs.
- Their product shape likely includes a browser extension or browser-mediated app linking,
  which aligns with a "sanitize selected text" workflow.
- They have a Partnerships role listed publicly, plus public contact at `team@tabflows.com`.

## Integration Concepts

### 1. Client-Side "Sanitize for AI" Action

Add a Tabflows action that appears when a clinician selects chart/message/lab text:

```text
Select text -> Sanitize for AI -> review safe prompt -> copy/open Claude/OpenEvidence/etc.
```

Why this is strong:

- Dead simple.
- Fits the tab-switching problem.
- Does not require deep EHR writeback.
- Can run local/client-side and avoid sending raw PHI to our infrastructure.

### 2. Patient Assist Minimum-Necessary Preprocessor

Use decon internally before Tabflows Patient Assist sends context into any model call.

This is the enterprise-grade trust story:

- Destination-specific minimization policy.
- Raw PHI only when truly required and covered.
- Category-level audit trail for what was removed.
- Risk gates for high-risk text.

### 3. Evidence Tool Bridge

Tabflows already lists OpenEvidence and UpToDate-style evidence workflows. Decon can be a bridge
for "ask evidence without over-sharing patient identity":

```text
patient chart context -> clinical question builder -> de-identified evidence query
```

This is closest to the original Haiku + Exa work.

### 4. Workflow Card: "Safe External Prompt"

Create a Tabflows workflow card that produces a sanitized prompt for external tools:

- Claude clinical reasoning prompt.
- ChatGPT patient education draft prompt.
- Perplexity search prompt.
- OpenEvidence search prompt.
- Referral summary prompt.

The key is making the destination explicit so the minimization policy can be stricter for
external tools than for BAA-covered internal flows.

## Suggested Pitch

Subject:

```text
Client-side PHI minimization for Tabflows AI handoffs
```

Short pitch:

```text
Tabflows is already becoming the operating layer across DPC tools. We have a decontextualization
prototype that strips patient identifiers and creates destination-specific, paste-ready clinical
prompts before context is sent to non-BAA or unknown-destination AI tools.

The strongest integration would be a Tabflows "Sanitize for AI" action: select chart/message/lab
context, run local/client-side PHI minimization, review the cleaned prompt, and then copy/open it
in Claude, OpenEvidence, Perplexity, or another destination. It gives clinicians a one-click
workflow while preserving Tabflows' trust story: minimum necessary, visible control, no raw PHI
leaving the protected workflow unless intentionally covered.
```

Proof points to attach:

- 132-query adversarial Haiku decon suite: zero real PHI leaks in the original architecture.
- 1132-query local OpenMed + regex evaluation: strong canonical PHI coverage, known gaps, and
  a concrete hybrid path for implicit/contextual identifiers.
- Current standalone decon package with tests passing locally.

## Risk and Positioning Notes

- Do not claim the tool makes any arbitrary prompt "HIPAA safe."
- Do not imply Tabflows currently exposes PHI unsafely.
- Use "minimum necessary", "destination-specific", "client-side", "visible controls", and
  "fail closed" language.
- Treat BAA status as destination-specific. Tabflows may have a BAA with its customers and
  subprocessors, but clinicians may still use external tools that do not.
- If Tabflows wants a hosted version, require a BAA and clear subprocessors before handling raw
  PHI server-side.

## Diligence Questions for Tabflows

1. Where does Patient Assist run, and which model vendors/subprocessors receive patient context?
2. Do they already perform field-level minimization before AI calls?
3. Does the browser surface have access to selected text from embedded app panes?
4. Is there an extension API or plugin surface for third-party actions?
5. Would they prefer a local companion, in-browser model, or server-side service under BAA?
6. Which customer workflows create the most risky copy/paste into external AI tools?
7. Can decon outputs become auditable metadata on tasks, comments, or Patient Assist actions?

## Partnership Recommendation

Start with a lightweight pitch and demo, not a full integration proposal.

Recommended demo:

- Local page with pasted Elation/Spruce-style snippet.
- Output modes for Claude, OpenEvidence, and web search.
- Risk gate with category-level audit.
- One Tabflows-shaped mock workflow: "select text from patient view -> sanitize -> open AI".

If they engage, propose a two-week technical spike:

- Confirm browser/extension integration surface.
- Run local decon on 50-100 synthetic DPC workflow snippets.
- Compare regex + OpenMed, local LLM fallback, and BAA-covered cloud rewrite.
- Produce a joint integration plan and compliance review checklist.

## Public Sources

- Tabflows home page: https://www.tabflows.com/
- Tabflows integrations page: https://www.tabflows.com/integrations
- Tabflows compliance page: https://www.tabflows.com/compliance
- Tabflows about page: https://www.tabflows.com/about
- HHS HIPAA de-identification guidance:
  https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html


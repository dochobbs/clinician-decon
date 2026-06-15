# Clinician Decon Tool Brief

**Date:** 2026-06-15
**Branch:** `clinician-decon-tool`
**Purpose:** Fork the existing decon work into a dead-simple clinician tool for moving
minimum-necessary, de-identified clinical context from a PHI-protected workflow into a
general LLM or web search surface when the clinician does not have a BAA with that downstream
tool.

## Product Thesis

Clinicians are already copying chart snippets, patient messages, labs, and visit context into
LLMs. Many do not know which tools are covered by a BAA, which prompts contain PHI, or how to
strip enough context without destroying clinical usefulness.

This project should become a "copy-safe clinical context builder":

1. Paste or capture PHI-containing text from a protected source.
2. Run local PHI minimization before anything leaves the clinician's machine.
3. Show a clean, paste-ready prompt for Claude, ChatGPT, Gemini, Perplexity, OpenEvidence, or
   a web search engine.
4. Display what was removed by category, not by value.
5. Fail closed when the remaining text looks re-identifiable.

The product should be explicit that it is a risk-reduction and minimum-necessary tool, not a
guarantee of HIPAA de-identification or legal clearance.

## Recommended Starting Shape

Build a local-first web app before a hosted SaaS product.

- Local web app: `localhost` UI with two panes: "Original clinical context" and "Safe prompt".
- One primary action: `Decontextualize`.
- One secondary action: `Copy for Claude`.
- Mode selector:
  - `Ask an LLM` maps to `external_general_llm`.
  - `Search the web` maps to `external_web_search`.
  - `Export / analytics` maps to `analytics_export`.
- Risk chip:
  - `Low`: copy allowed.
  - `Medium`: copy allowed with warning and highlighted risky leftovers.
  - `High`: copy disabled unless the user explicitly edits or reruns.
- Audit panel:
  - Removed categories: name, DOB, MRN, phone, email, URL, exact date, exact age, lab value,
    practice, relation, location.
  - Do not log the raw source text.

This maps cleanly to the current package, which already has task-specific minimization modes in
`src/decon/tasks.py`.

## Baseline Pipeline

Default path for the clinician tool:

```text
paste text
  -> deterministic regex scrub
  -> local PII/PHI NER
  -> risk scoring
  -> optional local LLM reviewer for hard cases
  -> safe prompt / safe search query
```

The default should not send raw PHI to a cloud LLM. Cloud rewriting is only acceptable when the
clinic has the right contractual coverage, or when the user explicitly chooses a non-default
advanced mode after a warning.

## Model and Method Lessons

| Approach | Why use it | Local? | Latency evidence | Quality evidence | Main risk |
|---|---|---:|---:|---|---|
| Regex pre-filter | Deterministic catch for SSN, phone, email, MRN, date, URL | Yes | Sub-ms in local docs | Fixes known MRN miss class | Brittle on implicit identifiers |
| OpenMed SuperClinical 434M NER | Local token classifier for names, MRNs, DOBs, contact info | Yes | 804 ms CPU in parity test | 1/18 identifiers leaked before regex fix; 0% canonical synthetic leak in 1000 queries | Misses non-canonical and contextual identifiers |
| OpenMed multilingual privacy filter | Fallback for Spanish or multilingual snippets | Yes | Not benchmarked here | Helpful for non-English, but local notes say it raised false positives | Larger 1B model; not default |
| Haiku-style LLM rewrite | Best at semantic decontextualization and implicit references | No, unless local equivalent | 1641 ms API in parity test; older architecture notes cite about 0.8s | 132 adversarial queries, zero real PHI leaks in original work | Raw PHI goes to the LLM unless covered by BAA |
| Local LLM reviewer | Recover semantic cases without cloud PHI transfer | Yes | Estimated 600 ms to 1.5s in local plan, needs validation | Best candidate for twins, family members, Spanish, SOAP notes, rare cases | Hardware/setup complexity |

## What to Build First

### v0: Demo Worth Showing

- Web UI for paste -> decon -> copy.
- Use current Python package for model-backed minimization where available.
- Add a local-only mode backed by the `cds-eval/eval/services/local_cds/decon.py` regex + OpenMed
  implementation.
- Include canned examples from the existing PHI stress fixtures.
- Show before/after plus removed category counts.

Success bar: a clinician can understand and use it in under one minute.

### v1: Local-First Clinician Utility

- Package as a one-command local app.
- Add browser-open startup flow.
- Store settings only locally.
- Add mode-specific prompts:
  - "Help me draft a message."
  - "Help me think through a differential."
  - "Find current guidelines."
  - "Summarize this for a referral."
- Add copy templates for Claude, ChatGPT, Perplexity, and web search.
- Add test corpus runner from the existing stress tests.

Success bar: no cloud dependency for default decon, and no raw prompt text persisted.

### v2: Browser Extension or Workflow Partner Integration

- Browser extension side panel or context-menu action: "Sanitize selection".
- Optional local native companion for model execution.
- Integration hook for workflow tools like Tabflows.
- Policy profiles by destination: Claude, ChatGPT, OpenEvidence, Perplexity, Google, internal EHR.

Success bar: the tool reduces risky copy/paste behavior inside the actual clinician workflow.

## UX Principles

- Default to local and fail closed.
- Avoid legalistic language in the main workflow; put details in a trust panel.
- Make the user inspect the clean prompt, not hidden automation.
- Show categories removed, never the removed PHI values.
- Keep the primary screen dense and utilitarian, not a landing page.
- Provide "why blocked" messages that are actionable:
  - "A likely MRN remains."
  - "A full date remains."
  - "A patient-specific URL remains."
  - "This text still includes family relationship identifiers."

## Compliance Framing

HHS describes two HIPAA de-identification methods: Expert Determination and Safe Harbor. It also
notes that de-identified data can retain some residual re-identification risk even when methods
are properly applied. This product should not claim that every output is legally de-identified.

Recommended language:

> This tool helps minimize PHI before using non-BAA tools. It does not replace legal review,
> a BAA, or the clinician's responsibility to confirm that the remaining text is appropriate
> for the intended destination.

## Evidence From Existing Work

- `docs/PHI_DECONTEXTUALIZATION_TESTING.md`: original Haiku decontextualization report; 132
  adversarial tests; zero real PHI leaks and one regex false positive.
- `docs/HAIKU_DECONTEXTUALIZATION_ARCHITECTURE.md`: three-layer defense with LLM rewrite,
  regex validation, and field separation.
- `/Users/dochobbs/Downloads/Consult/cds-eval/docs/openmed_vs_haiku_decon_results.md`:
  OpenMed vs Haiku parity test; OpenMed was faster and local but missed one MRN before the
  regex pre-filter.
- `/Users/dochobbs/Downloads/Consult/cds-eval/docs/decon_combined_1132q_findings.md`:
  1132-query local decon findings; local regex + NER is strong on canonical identifiers and
  weaker on implicit references, multilingual text, practice names, and contextual identifiers.

## External Sources

- HHS HIPAA de-identification guidance:
  https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html
- OpenMed SuperClinical model card:
  https://huggingface.co/OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1
- OpenMed multilingual privacy filter model card:
  https://huggingface.co/OpenMed/privacy-filter-multilingual

## Open Questions

- Is the first artifact a standalone local app, a browser extension, or both?
- Do we target individual clinicians first, or workflow vendors first?
- How much clinical detail should remain by default for "Ask an LLM" versus "Search the web"?
- Should the project support an optional BAA-covered cloud rewrite mode, or keep the first
  release strictly local?
- What name should this carry if it leaves the Amboss/decon project?


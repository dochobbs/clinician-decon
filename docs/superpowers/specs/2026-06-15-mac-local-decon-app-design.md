# Mac Local Decon App Design

**Date:** 2026-06-15
**Status:** Draft for review
**Repo:** `dochobbs/clinician-decon`

## Objective

Build a one-click Mac app that lets clinicians decontextualize PHI-containing clinical text
locally, review the cleaned prompt, then copy and open a third-party AI or evidence tool.

The app must be simple enough for a non-technical clinician:

1. Download app.
2. Open app.
3. Let it install the local privacy model automatically.
4. Paste clinical text.
5. Click `Decontextualize`.
6. Click `Copy & Open ChatGPT`, `Copy & Open Gemini`, `Copy & Open Claude`, `Copy & Open
   OpenEvidence`, `Copy & Open Web Search`, or `Copy Only`.

## Product Boundary

V1 is a local desktop app with a PWA-style interface, not a hosted SaaS product and not a browser
extension.

The app may open third-party web destinations after decon completes, but it must never send raw
PHI or decontextualized text to any Decon-hosted service. The handoff to third-party tools is
clipboard-based: copy the cleaned prompt, open the site, and require the clinician to paste and
review manually.

## Non-Negotiable Privacy Rules

- Decon runs locally by default.
- Raw pasted text never leaves the device.
- Raw pasted text is not stored on disk.
- Removed PHI values are not shown in the audit panel; only categories are shown.
- App logs must not include raw input, cleaned output, removed values, clipboard contents, or
  model token spans.
- Third-party links must not include the cleaned prompt in URL parameters.
- The app must not auto-submit to any third-party tool.
- If setup, model load, or risk scoring fails, decon fails closed.

## Target Platforms

### V1

- macOS first.
- Apple Silicon optimized.
- Intel Mac allowed if performance is acceptable.

### Later

- Windows installer.
- Browser extension.
- Tabflows or other workflow-tool integration.

## User-Facing System Requirements

Minimum Mac requirements:

- macOS 13 Ventura or newer.
- 8 GB RAM.
- 3 GB free disk space.
- Internet connection for first install/model download.
- Chrome, Safari, Arc, or another browser for destination tools.

Recommended Mac requirements:

- macOS 14 Sonoma or newer.
- Apple Silicon M1 or newer.
- 16 GB RAM.
- 5 GB free disk space.

Expected performance:

- Regex pass: effectively instant.
- Local OpenMed NER pass: target under 1 second on Apple Silicon for normal pasted text.
- Full decon result: target under 2 seconds for normal pasted chart/message snippets.
- Longer SOAP notes or copied chart bundles may take several seconds.

Unsupported or degraded:

- macOS versions older than 13.
- Machines with under 8 GB RAM.
- Managed devices that block unsigned/local model binaries.
- First-run offline setup before the model has been downloaded.

## Packaging Recommendation

Use a desktop shell with a PWA-style UI and local sidecar runtime.

Recommended implementation path:

- Tauri shell for the desktop app.
- React or equivalent web frontend inside the shell.
- Local sidecar service for decon execution.
- Python sidecar for V1 to reuse the existing `package/src/decon` code and the
  `from-cds-eval/local_cds/decon.py` OpenMed pipeline.

Fallback packaging path:

- Electron shell if Tauri/Python sidecar packaging slows the prototype.

Long-term hardening path:

- Replace or wrap Python sidecar with a more controlled runtime once the workflow is proven.
- Keep the same frontend and local API contract.

## First-Run Setup

On first launch, the app enters setup mode:

1. Checks OS version, architecture, RAM estimate, disk availability, and write access to app data.
2. Creates app directories:
   - macOS: `~/Library/Application Support/Decon/`
   - model cache: `~/Library/Application Support/Decon/models/`
   - logs: `~/Library/Logs/Decon/`
3. Downloads the local PHI model.
4. Validates checksum.
5. Runs a local smoke test on a synthetic PHI fixture.
6. Enables the main app.

Setup UI requirements:

- Progress state for download.
- Clear file size and remaining estimate when available.
- Resume after interrupted download.
- Retry button after failure.
- Explain that model setup is local and required before use.

Setup must not require terminal commands, Python knowledge, Homebrew, or manual model download.

## Model Strategy

V1 default stack:

```text
input text
  -> regex pre-filter
  -> OpenMed SuperClinical PHI-NER
  -> risk scoring
  -> destination-specific prompt formatting
```

Default model:

- `OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1`

Optional later model:

- `OpenMed/privacy-filter-multilingual` for multilingual fallback.

Cloud LLM rewrite:

- Not part of default V1.
- May be added later behind an explicit advanced setting for organizations with BAA coverage or
  approved cloud processing.

Local LLM reviewer:

- Not required for V1.
- Candidate V2 feature for hard semantic cases such as family relationships, multi-patient
  text, non-English snippets, and long copied notes.

## Core App Screen

The primary UI is a work surface, not a marketing page.

Required controls:

- Source text input.
- Destination selector:
  - ChatGPT
  - Gemini
  - Claude
  - OpenEvidence
  - Web Search
  - Copy Only
- Primary button: `Decontextualize`.
- Output prompt area.
- Risk indicator: Low, Medium, High.
- Removed categories panel.
- Buttons after successful decon:
  - `Copy & Open ChatGPT`
  - `Copy & Open Gemini`
  - `Copy & Open Claude`
  - `Copy & Open OpenEvidence`
  - `Copy & Open Web Search`
  - `Copy Only`

The destination button shown most prominently should match the selected destination.

## Third-Party Handoff

Destination URLs:

- ChatGPT: `https://chatgpt.com/`
- Gemini: `https://gemini.google.com/`
- Claude: `https://claude.ai/`
- OpenEvidence: configurable default, likely `https://www.openevidence.com/`
- Web Search: configurable default browser search page or search engine home page.

V1 handoff behavior:

1. Copy cleaned prompt to clipboard.
2. Open destination URL in the user's default browser.
3. Show local confirmation: `Cleaned prompt copied. Paste it into ChatGPT/Gemini/etc after
   reviewing.`

The app must not:

- Put prompt text in URL query parameters.
- Inject text into third-party web pages.
- Automate browser form filling.
- Auto-submit prompts.
- Use third-party APIs for destination handoff.

## Destination Prompt Templates

ChatGPT, Gemini, and Claude:

```text
Use the following de-identified clinical context. Do not assume missing patient identifiers.
If you need patient-specific details that are absent, say what is missing rather than inventing.

[SAFE_CONTEXT]
```

OpenEvidence:

```text
Find current clinical evidence or guidelines for the following de-identified clinical question:

[SAFE_QUERY]
```

Web Search:

```text
[SAFE_QUERY]
```

Copy Only:

```text
[SAFE_CONTEXT]
```

Templates should be editable later, but V1 can ship with fixed templates.

## Risk Handling

Low risk:

- Copy and destination buttons enabled.
- Removed category count shown.

Medium risk:

- Copy enabled.
- Warning shown.
- User must visually review output.
- Reasons shown by category, not value.

High risk:

- Copy and destination buttons disabled.
- User can edit source or output and rerun.
- App explains the likely issue:
  - possible MRN remains
  - possible date remains
  - possible patient URL remains
  - possible direct identifier remains
  - possible family relationship identifier remains

High-risk output cannot be copied through destination buttons in V1.

## Data Retention

V1 stores:

- app settings
- model files
- setup status
- destination preference
- non-sensitive telemetry only if explicitly enabled later

V1 does not store:

- raw input
- cleaned output
- clipboard text
- PHI spans
- removed values
- destination history containing prompt contents

Recent examples may use synthetic fixtures only.

## Error States

Required errors:

- Model not downloaded.
- Model checksum failed.
- Model load failed.
- Insufficient disk.
- Unsupported macOS version.
- Decon engine crashed.
- High-risk residual PHI detected.
- Clipboard copy failed.
- Browser open failed.

Every error should have one practical next action.

## Security and Trust Panel

The app should include a concise trust panel:

- Decon runs on this Mac.
- Raw pasted text is not sent to Decon servers.
- Cleaned prompts are copied only after review.
- The app does not make a legal guarantee of HIPAA de-identification.
- Clinicians remain responsible for destination choice and final prompt review.

Use this language in-product:

```text
This tool helps minimize PHI before using non-BAA tools. It does not replace legal review,
a BAA, or your responsibility to confirm that the remaining text is appropriate for the
destination.
```

## V1 Acceptance Criteria

Install/setup:

- A non-technical Mac user can install from a `.dmg`.
- First launch downloads and validates the model without terminal commands.
- App clearly handles interrupted model download and retry.

Core workflow:

- User can paste source text.
- User can select ChatGPT, Gemini, Claude, OpenEvidence, Web Search, or Copy Only.
- User can run decon locally.
- User can see cleaned prompt.
- User can see removed categories.
- User can copy and open the selected destination.

Privacy:

- No raw input appears in logs.
- No cleaned prompt appears in destination URL.
- No network call is made during decon after model setup.
- Destination opening only occurs after decon and user click.

Quality:

- Existing package tests pass.
- Regression tests cover canonical PHI: names, MRNs, DOBs, phone, email, SSN, URLs, exact dates.
- Regression tests cover V1 destination templates.
- Regression tests confirm high-risk outputs disable copy/open actions.

Performance:

- Normal snippets complete under 2 seconds on a recommended Apple Silicon Mac.
- App remains responsive during model load and inference.

## V1 Demo Script

Demo case 1: ChatGPT

1. Paste synthetic chart/message snippet with name, DOB, MRN, parent name, and clinical question.
2. Select ChatGPT.
3. Run decon.
4. Show removed categories.
5. Click `Copy & Open ChatGPT`.
6. Paste manually into ChatGPT.

Demo case 2: Gemini

1. Paste synthetic referral summary with direct identifiers.
2. Select Gemini.
3. Run decon.
4. Copy/open Gemini.

Demo case 3: OpenEvidence

1. Paste synthetic physician evidence question with patient details.
2. Select OpenEvidence.
3. Run decon.
4. Show concise evidence-query output.
5. Copy/open OpenEvidence.

## V2 Candidates

- Windows installer.
- Browser extension for selected text.
- Tabflows integration demo.
- Local multilingual fallback model.
- Local LLM reviewer for semantic/contextual identifier detection.
- Organization policy profiles.
- Admin-managed destination allowlist.
- Signed auto-updates.


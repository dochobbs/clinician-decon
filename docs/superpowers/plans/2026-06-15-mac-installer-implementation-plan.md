# Mac Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Clinician Decon as a one-click macOS app that starts the local decon service,
serves the existing PWA-style UI, and prepares first-run model setup without terminal commands.

**Architecture:** Use a small macOS desktop shell around the existing local app. V1 should keep
the Python decon package as a sidecar/runtime so the current local rules and future OpenMed NER
path remain reusable. The installer must preserve the privacy boundary: decon runs locally, no
raw input is logged, and third-party handoff remains copy/open only.

**Tech Stack:** macOS app bundle, Tauri or Electron shell, Python sidecar, existing
`package/src/decon` local API, app-data directories under `~/Library/Application Support/Decon/`,
GitHub Actions or local packaging script for repeatable `.dmg` builds.

---

## Source Docs

- Design spec: `docs/superpowers/specs/2026-06-15-mac-local-decon-app-design.md`
- Local app server: `package/src/decon/app_server.py`
- Web UI: `package/web/`
- Model setup status: `package/src/decon/model_setup.py`
- Headless release gate: `python3 package/scripts/run_validation.py`

## Task 1: Choose And Scaffold The Desktop Shell

**Files:**

- Create: `desktop/README.md`
- Create: `desktop/package.json` or equivalent shell manifest
- Create: `desktop/src/` shell source files
- Modify: root `README.md`

- [ ] Confirm Tauri first, Electron fallback only if Tauri sidecar packaging blocks progress.
- [ ] Scaffold the shell in `desktop/` without moving existing `package/` files.
- [ ] Make the first shell screen open the local UI surface.
- [ ] Add local dev command documentation.
- [ ] Run the shell locally and verify a blank app window opens.

Expected dev command shape:

```bash
cd desktop
npm install
npm run dev
```

## Task 2: Bundle Or Launch The Python Sidecar

**Files:**

- Create: `desktop/scripts/build-python-sidecar.sh`
- Create: `desktop/scripts/start-sidecar.*` if the shell needs a launcher wrapper
- Modify: desktop shell config
- Modify: `package/src/decon/app_server.py` only if it needs a configurable host/port

- [ ] Package or point the shell at a Python runtime strategy.
- [ ] Start `decon.app_server` from the desktop app on loopback only.
- [ ] Select an available localhost port or fail with a clear setup error.
- [ ] Stop the sidecar when the app exits.
- [ ] Verify the UI can call `/api/setup/status` and `/api/decon` through the shell.

Acceptance check:

```bash
curl -s http://127.0.0.1:<port>/api/setup/status
```

Expected: JSON response with `local_rules_ready: true` and `raw_phi_leaves_device: false`.

## Task 3: First-Run Model Setup Flow

**Files:**

- Modify: `package/src/decon/model_setup.py`
- Modify: `package/src/decon/app_server.py`
- Modify: `package/web/app.js`
- Modify: `package/web/index.html`
- Modify: `package/web/styles.css`
- Test: `package/tests/test_model_setup.py`
- Test: `package/tests/test_app_server.py`

- [ ] Extend setup status with OS/architecture/disk/RAM checks where available.
- [ ] Add a download-start endpoint only after deciding the downloader implementation.
- [ ] Save model metadata under `~/Library/Application Support/Decon/models/`.
- [ ] Validate checksum before marking the model installed.
- [ ] Show setup progress and retry state in the UI.
- [ ] Keep local-rules mode usable if the NER model is not installed, but label it clearly.

Privacy requirements:

- no raw pasted text in setup logs
- no model token spans in logs
- no network call during decon after setup

## Task 4: App Packaging

**Files:**

- Create: `desktop/scripts/package-mac.sh`
- Create: `desktop/packaging/entitlements.plist` if required
- Create: `desktop/packaging/README.md`
- Modify: `.gitignore` for build outputs

- [ ] Build an unsigned local `.app` first.
- [ ] Wrap the `.app` in a `.dmg`.
- [ ] Document local Gatekeeper expectations for unsigned builds.
- [ ] Add signing/notarization placeholders only as explicit future steps, not fake-complete config.
- [ ] Verify a clean machine or clean user account can open the app and reach setup.

Expected output:

```text
desktop/dist/Clinician Decon.dmg
```

## Task 5: Release Gate

**Files:**

- Create: `.github/workflows/validate.yml` if GitHub Actions is enabled for this repo
- Modify: `package/README.md`
- Modify: `docs/qa/headless-validation.md`

- [ ] Run unit tests before packaging.
- [ ] Run headless validation before packaging.
- [ ] Fail packaging if validation fails.
- [ ] Save validation JSON as a build artifact where CI supports it.

Required local release gate:

```bash
python3 -m pytest package/tests
python3 package/scripts/run_validation.py --report package/reports/latest-validation.json
```

## Task 6: Installer QA

**Files:**

- Create: `docs/qa/mac-installer-qa.md`

- [ ] Document smoke steps for install, launch, setup status, decon, copy/open handoff, and quit.
- [ ] Include at least three synthetic snippets: canonical vaccine, adversarial prompt injection,
  and OCR-spaced identifiers.
- [ ] Confirm no raw PHI appears in logs.
- [ ] Confirm no prompt text appears in third-party URLs.
- [ ] Confirm the app handles interrupted model download and retry once model download exists.

## Initial Success Bar

The first shippable Mac installer does not need the OpenMed model fully wired if the UI clearly
states local-rules mode. It does need:

- one-click `.dmg` install
- app opens without terminal
- local decon server starts and stops with the app
- current headless validation passes before packaging
- copy/open handoff works for ChatGPT, Gemini, Web Search, and Copy Only
- no raw input or cleaned prompt in logs or URLs

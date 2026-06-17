# Local Decon Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable local prototype for the Mac-first Decon app.

**Architecture:** Add a local deterministic decon engine, destination template/handoff module,
stdlib HTTP server, and static PWA-style frontend inside `package/`. The prototype runs fully
locally, copies cleaned prompts, and opens third-party destinations without placing prompt text in
URLs.

**Tech Stack:** Python stdlib HTTP server, existing `decon` Python package, static HTML/CSS/JS.

---

### Task 1: Destination Handoff

**Files:**
- Create: `package/src/decon/destinations.py`
- Test: `package/tests/test_destinations.py`

- [ ] Write tests proving external tool, external tool, external tool, external tool, Web Search, and Copy Only render
      prompts and never embed prompt text in destination URLs.
- [ ] Implement `render_prompt(destination_id, safe_context, safe_query=None)`.
- [ ] Implement `build_handoff(destination_id, prompt)` returning copy text, URL, and action label.
- [ ] Run `python -m pytest package/tests/test_destinations.py -q`.

### Task 2: Local Rules Decon Engine

**Files:**
- Create: `package/src/decon/local_rules.py`
- Test: `package/tests/test_local_rules.py`

- [ ] Write tests proving common identifiers are removed from returned safe text.
- [ ] Write tests proving removed values are not returned in category summaries.
- [ ] Write tests proving high-risk residual identifiers disable copy/open.
- [ ] Implement regex spans, replacement, category counts, and risk scoring.
- [ ] Run `python -m pytest package/tests/test_local_rules.py -q`.

### Task 3: Setup Status

**Files:**
- Create: `package/src/decon/model_setup.py`
- Test: `package/tests/test_model_setup.py`

- [ ] Write tests proving setup status is local and points to an app-data model directory.
- [ ] Implement app data directory resolution and non-network status checks.
- [ ] Implement an install hook that can later call Hugging Face download machinery.
- [ ] Run `python -m pytest package/tests/test_model_setup.py -q`.

### Task 4: Local HTTP App

**Files:**
- Create: `package/src/decon/app_server.py`
- Create: `package/web/index.html`
- Create: `package/web/styles.css`
- Create: `package/web/app.js`
- Create: `package/web/manifest.json`
- Create: `package/web/sw.js`
- Test: `package/tests/test_app_server.py`

- [ ] Write tests for `POST /api/decon` behavior through handler helpers.
- [ ] Implement JSON API helpers independent of the HTTP server.
- [ ] Implement `python -m decon.app_server` serving `package/web`.
- [ ] Implement UI controls for paste, destination, decon, risk, category summary, copy, and open.
- [ ] Run relevant tests.

### Task 5: Repo Verification

**Files:**
- Modify: `package/README.md`
- Modify: `README.md`

- [ ] Document local prototype command.
- [ ] Run full package tests.
- [ ] Run the app locally and smoke test the API.
- [ ] Commit and push.

# Repository Map

This file is a public-facing map of the current repository. It intentionally omits local machine
paths, historical source locations, and partner or vendor provenance.

## `package/`

Main runnable package.

- `src/decon/`: local decontextualization code, app server, CLI entrypoints, validation runner,
  OpenMed setup/status checks, and destination handoff rendering.
- `web/`: local browser UI, manifest, service worker, and styles.
- `tests/`: unit and regression tests.
- `data/`: checked-in synthetic and adversarial validation suites.
- `scripts/`: trace generation and validation wrappers.
- `reports/`: generated validation reports retained for QA history.
- `docs/`: package-level tool brief and historical implementation notes.

## `docs/qa/`

Quality and validation documentation.

- headless validation runbook
- query-set registry
- synthetic trace generation strategy
- persona library notes
- local-rules and model-backed pipeline audits
- external baseline comparisons and error samples
- focused PHI-field and blind-spot red-team reports
- Mac installer QA

## `docs/superpowers/`

Planning and design artifacts.

- prototype implementation plan
- local app design
- Mac installer implementation plan
- persona trace generator design
- PHI-field handling review

## `docs/install/`

End-user and pilot-install documentation.

- Mac clean install path
- demo-facing DMG readme

## `installer/mac/`

Repeatable Mac bootstrap packaging assets.

- `build_self_contained_dmg.sh`: creates the doctor-facing all-in-one DMG
- `build_dmg.sh`: creates the smaller bootstrap pilot DMG
- `create_icon_assets.py`: generates Finder, browser, and PWA icon assets
- `assets/ClinicianDecon.icns`: app bundle icon
- `app/Info.plist`: app bundle metadata
- `app/clinician-decon-launcher`: first-run runtime/model setup and local app launcher

## Historical Fixtures

Some historical fixtures and reports are retained for regression continuity. They should be treated
as internal QA material, not as current product documentation.

## Public-Ready Starting Points

For a fresh reader, start here:

- `README.md`
- `package/README.md`
- `docs/install/mac-clean-install.md`
- `docs/install/mac-demo-readme.md`
- `docs/qa/headless-validation.md`
- `docs/qa/mac-installer-qa.md`
- `docs/qa/query-set-registry.md`
- `package/docs/clinician-decon-tool-brief.md`

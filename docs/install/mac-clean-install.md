# Mac Clean Install

This is the clean-install path for the current Mac bootstrap DMG. It is intended for local testing
and pilot review before a signed, notarized clinical installer.

## What The DMG Does

The DMG contains `Clinician Decon.app` and a read-me. The app bundles the source package, then on
first launch creates a per-user runtime under:

```text
~/Library/Application Support/Clinician Decon
```

The first launch attempts to:

1. create `venv/` in the app-support directory,
2. install the bundled decon package with OpenMed runtime dependencies,
3. download OpenMed model files into the app-support model cache,
4. start the local web app on `127.0.0.1:8769`,
5. open the local app in the user's browser.

The model files are not bundled in the DMG. The current OpenMed model cache is about 1.6 GB after
download, and the Python dependency install can require several additional GB during setup.

## Clean Mac Requirements

Minimum pilot requirements:

- macOS 13 or newer.
- Apple Silicon or Intel Mac.
- Python 3 with `venv` support available as `/usr/bin/python3` or through `DECON_PYTHON`.
- Internet access for first-run Python dependencies and OpenMed model download.
- At least 8 GB RAM; 16 GB is preferred for model-backed local NER.
- At least 8 GB free disk for the runtime, package cache, model file, and temporary install files.

For a release-grade one-click clinical installer, the next packaging step is to bundle a signed
Python runtime and prebuilt dependencies so clinicians do not need a separate Python install.

## Install Steps

1. Open `Clinician-Decon-0.1.0.dmg`.
2. Drag `Clinician Decon.app` to `Applications`.
3. Open `Clinician Decon.app`.
4. Wait for first-run setup. This can take several minutes because dependencies and model files are
   downloaded locally.
5. When the browser opens, confirm the setup badge says the local model is ready.
6. Paste only synthetic or approved test text during QA.

If macOS blocks the unsigned app, use right-click, Open, then confirm. This is expected for the
unsigned bootstrap DMG. Signing and notarization are required before broad external distribution.

## Privacy Boundary

- raw pasted text stays on 127.0.0.1.
- The app does not put prompt text in third-party URLs.
- Model setup may contact package/model hosts, but decon should use local files after setup.
- Logs live in `~/Library/Application Support/Clinician Decon/logs/`.
- Setup logs should contain install output only, not pasted clinical text.

## Reset Or Uninstall

Quit the app, then remove:

```text
/Applications/Clinician Decon.app
~/Library/Application Support/Clinician Decon
```

The app does not install a launch agent, background service, browser extension, or system-wide
configuration.

## Build The DMG From A Checkout

From the repository root:

```bash
installer/mac/build_dmg.sh
```

Expected output:

```text
dist/mac/Clinician-Decon-0.1.0.dmg
```

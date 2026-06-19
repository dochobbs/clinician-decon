# Clinician Decon Package Audit

This file is included in the DMG so a reviewer can see what is inside the app before trusting it.
The Mac app is not distributed through the App Store in this demo build, so the package should be
easy to inspect.

## What The App Contains

- `Clinician Decon.app`: a native macOS wrapper around the local web UI.
- `Contents/MacOS/ClinicianDeconNative`: the small native WebKit window wrapper.
- `Contents/MacOS/clinician-decon-launcher`: starts and stops the local Python privacy server.
- `Contents/Resources/package`: the Python package, local web UI, validation code, and CLI code.
- `Contents/Resources/python`: bundled Python runtime for the self-contained DMG.
- `Contents/Resources/python-packages`: bundled Python dependencies needed by the local model path.
- `Contents/Resources/package/local-models`: bundled OpenMed model files for local PHI NER.
- `Contents/Resources/ClinicianDecon.icns`: generated app icon.
- `Contents/Resources/LICENSE`: project license.
- `Contents/Resources/README_FIRST.md`: short install and use notes.
- `Contents/Resources/PACKAGE_AUDIT.md`: this audit manifest.

## Runtime Boundary

- The app binds only to `127.0.0.1:8769`.
- The browser or native window talks to that local address.
- Raw pasted source text is sent only to the local process on the same Mac.
- The decon engine requests `rules+openmed`; if OpenMed is unavailable, copy should be blocked.
- External tool buttons open static third-party URLs only after the scrubbed draft is copied.
- The app is not a full chart de-identification export; the clinician remains the final reviewer.

## What Gets Stored

- App support files live under `~/Library/Application Support/Clinician Decon`.
- Logs live under `~/Library/Application Support/Clinician Decon/logs`.
- Logs should contain setup/server status and model-loading events, not raw pasted clinical text.
- The app writes `server.pid` while the local server is running and removes it during cleanup.

## What Is Not Included

- No cloud API keys.
- No real patient data.
- No telemetry endpoint.
- No remote decon service.
- No App Store receipt or notarization metadata in the demo build.

## How To Audit Quickly

1. Mount the DMG.
2. Right-click `Clinician Decon.app` and choose `Show Package Contents`.
3. Inspect the files listed above.
4. Launch the app and confirm the status pill says `Running on this Mac`.
5. Click `Quit`, then confirm `http://127.0.0.1:8769/api/setup/status` no longer responds.

## Source Of Truth

The project source repo should match the package contents for the same build. Regenerate the icon
assets with `installer/mac/create_icon_assets.py` and regenerate the DMG with
`installer/mac/build_self_contained_dmg.sh`.

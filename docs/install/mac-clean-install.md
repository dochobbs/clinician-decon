# Mac Clean Install

This is the clinician-facing Mac install path: download the self-contained DMG, drag the app to
Applications, open it, and use the local browser app. A busy clinician should not need Terminal,
Python, pip, or a model download.

## Primary Artifact

Build the self-contained DMG from the repository root:

```bash
installer/mac/build_self_contained_dmg.sh
```

Expected output on Apple Silicon:

```text
dist/mac/Clinician-Decon-0.1.0-self-contained-arm64.dmg
```

The self-contained DMG bundles:

- `Clinician Decon.app`
- a bundled Python runtime under `Contents/Resources/python/`
- installed Python packages under `Contents/Resources/python-packages/`
- installed OpenMed runtime dependencies
- the bundled decon package
- OpenMed model files under `Contents/Resources/package/local-models/`

OpenMed model files are bundled in this self-contained DMG. They are still not tracked in git; the
build script copies them from the repo-local ignored model directory during packaging.

## Clinician Install Steps

1. Open `Clinician-Decon-0.1.0-self-contained-arm64.dmg`.
2. Drag `Clinician Decon.app` to `Applications`.
3. Right-click `Clinician Decon.app`, choose Open, and confirm if macOS warns because the demo
   build is unsigned.
4. Wait for the local browser app to open at `http://127.0.0.1:8769/`.
   The browser tab is the app window; the Mac app is only the local launcher.
5. Confirm the setup badge says the local model is ready.

There should be no dependency setup prompt, model download, or Terminal command on first launch.

## Basic Use

1. Paste clinical text from a PHI-protected source into `Source`.
2. Choose `For use in` to format the handoff for the destination tool.
3. Click `Decontextualize`.
4. Review the safe prompt and removed categories.
5. Click `Copy & Open` or `Copy Only`.

Use the `Example` menu to load synthetic cases that exercise common workflows.

## Launch Surface

The current demo opens the local app in a browser tab. That keeps the installer simple, but the
better release path is a small macOS window wrapper around the same local web UI. A wrapper would
feel like a normal app, while keeping the tested local server, OpenMed runtime, and browser-based
interface intact.

## Mac Requirements

Pilot minimum:

- macOS 13 or newer.
- Apple Silicon for the current `arm64` artifact.
- At least 8 GB RAM; 16 GB is preferred for comfortable local model execution.
- At least 6 GB free disk for the app bundle, copied app, and local logs.

For Intel Macs, build on Intel or provide a separate `x86_64` self-contained artifact.

## Privacy Boundary

- raw pasted text stays on 127.0.0.1.
- The app does not put prompt text in third-party URLs.
- The self-contained app should not contact the network during decon.
- Logs live in `~/Library/Application Support/Clinician Decon/logs/`.
- Logs should contain startup/setup events only, not pasted clinical text.

## Close Or Quit

Closing the browser tab closes only the visible UI. It does not stop the local server.

To fully quit the local app and release memory:

1. Click `Quit` in the top-right app controls.
2. Wait for the page to say the local app stopped.
3. Close the browser tab.

After that, reopen `Clinician Decon.app` from Applications when you want to use it again.

## Reset Or Uninstall

Click `Quit`, then remove:

```text
/Applications/Clinician Decon.app
~/Library/Application Support/Clinician Decon
```

The app does not install a launch agent, background service, browser extension, or system-wide
configuration.

## Bootstrap Fallback

There is also a smaller bootstrap DMG:

```bash
installer/mac/build_dmg.sh
```

Expected output:

```text
dist/mac/Clinician-Decon-0.1.0.dmg
```

The bootstrap DMG is for development and pilot troubleshooting only. It requires Python 3 with
`venv` support and downloads dependencies/model files on first launch. Do not treat it as the
busy-clinician installer.

## Signing And Notarization

The local build can be unsigned or ad-hoc signed for internal testing. Broad external distribution
requires Developer ID signing and Apple notarization so clinicians do not see trust warnings.

# Clinician Decon Demo Install

This DMG is for demoing Clinician Decon on an Apple Silicon Mac.

## Install

1. Drag `Clinician Decon.app` to `Applications`.
2. Open `Applications`.
3. Right-click `Clinician Decon.app`, choose `Open`, then confirm. This step is needed because
   this demo build is unsigned.
4. A browser tab should open automatically at:

```text
http://127.0.0.1:8769/
```

The app runs locally. No clinical text is sent during decontextualization unless you copy the
cleaned prompt into another tool yourself.

## Demo Check

Paste this synthetic snippet:

```text
Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 asks about HPV vaccine.
```

Expected output:

```text
[NAME] adolescent [MRN] asks about HPV vaccine.
```

The model status should show the local model is ready.

## Quit

Closing the browser tab closes only the visible UI. To fully stop the local app, click
`Quit Local App` in the Local Boundary section, then close the tab.

## Notes

- The OpenMed model and Python runtime are bundled in this demo app.
- The browser tab is the app window. The Mac app itself is only a local launcher.
- If launch takes more than a few seconds, macOS should show a startup notification.
- Signing and notarization are still required before broad distribution.

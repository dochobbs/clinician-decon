# Clinician Decon Demo Install

This DMG is for demoing Clinician Decon on an Apple Silicon Mac.

## Install

1. Drag `Clinician Decon.app` to `Applications`.
2. Open `Applications`.
3. Right-click `Clinician Decon.app`, choose `Open`, then confirm. This step is needed because
   this demo build is unsigned.
4. A `Clinician Decon` app window should open automatically.

The app runs locally. No clinical text is sent during decontextualization unless you copy the
cleaned prompt into another tool yourself.

## Basic Use

1. Paste clinical text into `Source`.
2. Choose `For use in`.
3. Click `Decontextualize`.
4. Review the safe prompt before copying.

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

To fully stop the local app, click `Quit` in the top-right app controls, then close the app
window. Closing the app window also stops the local server.

## Notes

- The OpenMed model and Python runtime are bundled in this demo app.
- The Mac app uses a native window around the local web UI.
- External destinations open in the default browser only after you click `Copy & Open`.
- If launch takes more than a few seconds, macOS should show a startup notification.
- Signing and notarization are still required before broad distribution.

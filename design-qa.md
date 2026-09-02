# Decon Design QA

source visual truth: [`decon-mockup.html`](decon-mockup.html)

source screenshot: `/private/tmp/decon-mockup-source.png`

implementation screenshot: `/private/tmp/decon-redesign-desktop.png`

comparison screenshot: `/private/tmp/decon-design-qa-comparison.png`

additional responsive evidence: `/private/tmp/decon-redesign-narrow.png`, `/private/tmp/decon-redesign-stacked.png`

viewport: Chrome window bounds `{90, 70, 1510, 1000}` for desktop; narrower windows at `{100, 80, 980, 1000}` and `{120, 80, 820, 1000}`.

state: idle visual comparison. The local API post-run path was also smoke-tested with a synthetic vaccine callback and returned `removed_spans` offset metadata plus fail-closed behavior when OpenMed was unavailable in the source checkout.

full-view comparison evidence: side-by-side comparison screenshot at `/private/tmp/decon-design-qa-comparison.png`.

focused region comparison evidence: no separate crop needed; header, boundary banner, panels, seam, action rows, and ledger are readable in the full comparison capture.

**Findings**

- No P0/P1/P2 findings remain.

**Patches Made Since Previous QA Pass**

- Rebuilt the shell around the handoff structure: wordmark/tagline, local status rail, boundary banner, split warm/cool page background, two-panel stage, center seam, and ledger.
- Renamed the right panel from `Safe Prompt` to `Scrubbed draft`, changed the primary action from `Decontextualize` to `Reduce`, and changed the copy action to `Copy across ->`.
- Added source-span highlighting after a run using server-returned offset/category/confidence metadata, without returning removed PHI values.
- Added always-on residual-risk prompts for initials/nicknames/single first names and relationship-based identifiers, plus conditional prompts for dates and place-like categories.
- Added responsive wrapping so desktop action rows stay on one line, narrow panes collapse controls cleanly, and panels stack below the breakpoint.
- Added courier animation scaffolding for `Copy across ->`, with `prefers-reduced-motion` support.
- Bumped the service worker cache to avoid stale UI shells.

**Open Questions**

- The header and boundary icons use the existing app icon asset instead of the mockup's temporary CSS glyph/lock. This keeps the shipped app on real assets and avoids adding throwaway icon drawings.
- The source checkout did not have the OpenMed model configured, so the live source-server run correctly reported local-rules fallback and blocked copy. The self-contained packaged app should be smoke-tested after the next DMG rebuild to verify the same UI with bundled OpenMed.
- Chrome blocks JavaScript execution from Apple Events on this machine. Keyboard/click smoke testing was limited; API and visual layout were verified directly.
- The new `decon-mark.svg` seam-and-dot mark is now used directly in the web UI and as the source for regenerated PNG, ICO, and ICNS assets.

**Implementation Checklist**

- Re-run full package tests.
- Rebuild the self-contained DMG.
- Launch the rebuilt DMG and verify the header status, local model readiness, sample reduction, highlighted source, ledger, and shutdown.

**Follow-up Polish**

- Replace the IBM Plex Sans fallback with licensed FF Meta when available.

final result: passed

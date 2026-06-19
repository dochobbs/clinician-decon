# Decon — Design Handoff for Claude Code

**Product:** A local-first clinical utility that strips identifiers out of clinical text *before* a clinician pastes it into an external LLM (ChatGPT, Claude, etc.). Runs on the clinician's own Mac; raw text never leaves the machine.

**This doc's job:** give you everything to build the UI faithfully — tokens, copy, components, states, behaviors — and, just as important, the *reasoning* behind each choice so you don't optimize it away. A reference mockup (`decon-mockup.html`) accompanies this; treat it as the source of truth for layout and motion, and this doc as the source of truth for intent.

> **How to read the callouts:** lines marked **🔒 Do not revert** are deliberate against an obvious "improvement." If a change seems like a clear upgrade, check here first.

---

## 1. The one idea everything serves

Decon makes **two different promises**, and the entire design exists to keep them from blurring:

| Promise | Claim | Strength | Whose job |
|---|---|---|---|
| **Confidentiality** | Did the raw text leave this Mac? | **Strong & true** — lean on it hard | The tool's |
| **Completeness** | Did we catch *every* identifier? | **Weak** — local matching misses initials, nicknames, oblique relational tells | **The clinician's** |

Every copy and layout decision below either *maximizes the confidentiality promise* or *minimizes the completeness promise and hands the last check to the human*. If you're ever unsure how to word or place something, resolve it in that direction.

🔒 **Do not revert:** never imply the output is "clean," "safe," "de-identified," or "done." It is a reduced draft that a human must review.

---

## 2. Naming & copy (load-bearing — use these exact strings)

The product is **Decon** — framed as *reduce before you send*, **not** *sterilize*. (We considered renaming to Anteroom/Airlock; client chose to keep Decon with the reduced-not-cleaned meaning.)

| Location | String |
|---|---|
| Wordmark | `Decon` |
| Tagline | `Strip identifiers before you paste into an outside tool — on this Mac, then you check it.` |
| Local status pill | `Running on this Mac` |
| Boundary banner | **`The original text stays on this Mac.`** ` Only what you copy crosses the line — and only after you've read it.` |
| Left panel title | `Source` · sub: `chart note · portal message · callback` |
| Right panel title | `Scrubbed draft` · sub: `your review before it leaves` |
| Primary action (left) | `Reduce` |
| Primary action (right) | `Copy across →` |
| Secondary action (right) | `Copy only` |
| Empty draft state | `Your scrubbed draft will appear here for review.` |
| Ledger column A | `What was pulled` |
| Ledger column B | `What to double-check` |
| Ledger column C | `Local boundary` |
| Local-boundary body | `A local, safer prompt for an outside tool when you don't want raw PHI to leave this Mac. Not a full chart de-identification export — you are the last check.` |
| Seam micro-label | `on this mac → leaves this mac` |

🔒 **Do not revert — the three highest-leverage strings:**
1. **Right panel is `Scrubbed draft`, never `Safe Prompt`.** "Safe" reads as *cleared, ship it* and buries the human's review step. "Draft" signals *you're not done.*
2. **Status reads `Nothing sent yet` / `Reading on this Mac…`, never `Not run`.** "Not run" looks like an error; these read as calm and reinforce *local*.
3. **The boundary banner is a persistent, prominent element — not footer fine print.** It's the product's entire reason to exist.

State the user's job in plain verbs. Don't make them name their own text "PHI" — show examples instead.

---

## 3. Design tokens

Calm clinical utility. One accent (teal = *local / safe*), one caution tone (amber, used sparingly = *verify this*), generous whitespace. Mono only for the actual text payloads, so source and draft read as *artifacts being handled*, not chrome.

### Color
```
--ink:        #15211d   /* pine-tinted near-black, primary text */
--ink-soft:   #46554f   /* secondary text */
--ink-faint:  #6e7d77   /* tertiary / captions */
--ground-in:  #fbfaf6   /* warm — the "inside this Mac" half */
--ground-out: #eef2f2   /* cool — the "outside-facing" half */
--surface:    #ffffff
--line:       #e4e3db   /* warm hairline */
--line-cool:  #d9e1e0   /* cool hairline (draft side) */
--teal:       #1c6b58   /* primary accent: local/safe */
--teal-deep:  #13503e
--teal-tint:  #e6f0ec
--teal-tint-2:#d6e7e0
--amber:      #a8631a   /* caution: worth-a-look */
--amber-tint: #f7eede
--amber-line: #ecd9b8
```

### Type
- **UI:** humanist sans. The mockup uses **IBM Plex Sans** as a stand-in. ⚠️ **The shipped brand face is Meta (FF Meta).** Meta isn't web-licensed in the mockup environment — swap it back when you have the license; Plex Sans is the fallback, not the target.
- **Text payloads (source + draft):** **IBM Plex Mono** — this is intentional and brand-consistent; keep it.

### Shape & motion
```
--r: 14px (cards) · --r-sm: 9px (buttons/inputs)
focus ring: 3px var(--teal-tint) + 1px var(--teal) border
```

---

## 4. Layout

Three regions stacked vertically inside a `max-width: ~1180px` centered column:

```
+--------------------------------------------------------------+
| HEADER:  [glyph] Decon   tagline ...    * Running on Mac · Quit|
+--------------------------------------------------------------+
| BOUNDARY BANNER: original stays on this Mac. only copy crosses |
+--------------------------------------------------------------+
| STAGE (the workspace)                                         |
| +-----------------+ || +----------------------------------+   |
| | SOURCE (warm)   | || | SCRUBBED DRAFT (cool)            |   |
| | For use in [v]  |SEAM| status pill                      |   |
| | [mono textarea] | || | [mono textarea / empty state]    |   |
| | [Reduce] ex Load| || | [Copy across ->] [Copy only]     |   |
| +-----------------+ || +----------------------------------+   |
+--------------------------------------------------------------+
| LEDGER: What was pulled | What to double-check | Local boundary|
+--------------------------------------------------------------+
```

**The page background itself is split** warm-left / cool-right at the 50% line (`linear-gradient` with a hard stop), so *before any text is read*, the screen already communicates **inside this Mac** vs. **outside-facing**. This is structural, not decorative — keep it.

On `max-width: 840px`: panels stack, the seam is hidden, ledger columns stack.

---

## 5. The signature element — the seam

🔒 **This is the one thing the product is remembered by. Spend the design budget here; keep everything else quiet.**

A hairline runs vertically down the center of the stage with a **rotated mono micro-label** (`on this mac → leaves this mac`). It is the literal threshold the content crosses. The thesis: *privacy is more believable as geography than as a paragraph.*

**The courier animation** — when the user hits **Copy across →**, a small chip (`scrubbed draft →`) physically flies left-to-right *across the seam* to the outside panel. This makes the air-gap legible as motion: the user *watches* only the scrubbed version cross, while the original stays put.

```
keyframes "cross": start just left of seam, fade in,
travel a computed distance to the right panel edge, fade out.
~900ms, ease cubic-bezier(.5,.05,.2,1).
Distance is computed from live element rects (seam + stage),
not hardcoded — recompute on each fire so it survives resize.
```

🔒 **Respect `prefers-reduced-motion`:** disable the courier flight and the pulsing local-dot; the copy still works, just without the travel.

---

## 6. Component specs

### Header
- Glyph + `Decon` wordmark + tagline on the left; `Running on this Mac` pill (with a softly pulsing teal dot) + `Quit` on the right.
- The local pill is the best reassurance on the page — three words, says *local*. Keep it visible at all times.

### Boundary banner
- Full-width card directly under the header. Lock icon in a teal tint, bold first clause, regular second clause. Always visible; never collapses into the ledger.

### Source panel (warm)
- Title + `For use in [target v]` selector (ChatGPT / Claude / Gemini / Copilot / Other).
- Mono `textarea`, placeholder `Paste the source text here…`.
- Action row: `Reduce` (primary) · `Example [v] Load` · spacer · `Clear`.
- **After a run**, the textarea is replaced by a **read-only highlighted view** of the source (see §7) with an `← Edit source` link to return. *(See open question 11.1 — this tradeoff is not finalized.)*

### Draft panel (cool)
- Title + status pill (right-aligned).
- Empty state (dashed border, centered icon + `Your scrubbed draft will appear here for review.`) until a run completes, then a mono `textarea` holding the draft (editable — the clinician may hand-fix).
- Action row: `Copy across →` (primary) · `Copy only`. Both disabled until a draft exists.

### Ledger (3 columns)
- **What was pulled:** chips per category. Teal chip = confident; amber chip = *worth a look*. A small legend (`confident` / `worth a look`) appears only when there are results.
- **What to double-check:** see §8 — this is the column that actively recruits clinician judgment.
- **Local boundary:** the scope statement + an `Engine · …` status line in mono.

---

## 7. The highlight-the-source behavior (teaching the diff)

After **Reduce**, the left panel shows the *original* text with pulled spans marked **in situ**:
- `mark.c1` (confident) → teal tint.
- `mark.c0` (worth-a-look) → amber tint. **Loose dates and place names get amber** because that's exactly where automatic matching is weakest.

Purpose: the tool earns trust *by showing what it changed and admitting where it's guessing.* The amber spans are an honesty signal — "look harder here." Don't flatten everything to one confidence level.

---

## 8. "What to double-check" — residual-risk prompts

🔒 **This column is the ethical core. It surfaces failure modes the matcher cannot catch.** Always include the first two; add the others conditionally.

Always-on:
- *Initials, nicknames, and single first names often slip past automatic scrubbing — reread for them.*
- *A relationship can identify a patient with no name attached ("mom is a nurse here," "dad coaches at the high school"). Reread for these.*

Conditional:
- If any **loose date** was pulled/flagged: *Loose dates near a small practice can re-identify even after names are gone — confirm each one in amber.*
- If any **place** was pulled: *Specific places (clinic site, pharmacy, school) narrow the field fast in a small community.*

⚠️ These prompts are the part most worth replacing with the client's **real residual-risk taxonomy** — treat the current list as a working placeholder, not the final clinical content.

---

## 9. States

| State | Pill copy | Pill style | Engine line |
|---|---|---|---|
| idle | `Nothing sent yet` | neutral | `Engine · idle` |
| reading | `Reading on this Mac…` | amber, blinking dot | `Engine · reading locally…` |
| ready | `Draft ready · your review` | teal | `Engine · reduced locally · N categories` |
| copied | `Copied across` | teal | `Engine · copied to clipboard · original never left` |

🔒 The `reading` state must say *Reading on this Mac* (not a generic spinner). The local processing is the differentiator — let the user watch it happen rather than wonder if data is being uploaded.

---

## 10. Behaviors & wiring

- **Load:** fills the source with the selected synthetic example. *(The mockup ships 3 synthetic, PHI-free examples: vaccine callback, portal message, med refill. Keep examples obviously synthetic.)*
- **Reduce:** disables itself → `reading` (~700ms) → swaps source to highlighted view, fills draft, populates ledger → `ready`.
- **Copy across →:** writes draft to clipboard, fires courier, sets `copied`, button reads `Copied ✓` for ~1.6s. **Copy only:** same clipboard write, no courier.
- **Target change** (`For use in`): if a draft exists, re-run so the draft's target-appropriate preamble updates.
- **Clear:** resets everything to idle.
- **Edit source:** returns highlighted view to editable textarea.

⚠️ **The reducer in the mockup is illustrative regex/heuristics, NOT the real engine.** Real implementation must call the actual local model. Keep the mockup's honesty footer (reworded) in production: don't let the demo's pattern-matching masquerade as the shipped reducer.

---

## 11. Open decisions (not finalized — flag, don't silently resolve)

1. **Highlight vs. live edit.** Freezing the source into a highlighted diff teaches well but blocks fast tweak-and-re-run until "Edit source." Some clinicians will want to edit and re-reduce rapidly. If you have a cleaner pattern (e.g., an inline highlight *overlay* on a still-editable field), propose it.
2. **Meta font.** Ship target is FF Meta for UI; Plex Sans is only the unlicensed-environment fallback.
3. **Real engine integration.** The local model and its actual category taxonomy replace the demo heuristics; the residual-risk prompts (§8) should map to that taxonomy.

---

## 12. The icon

**Current mark:** a teal rounded square (`--teal`), a faint white seam down the center, a single white dot just left of the seam.

**Concept:** the mark is a miniature of the workspace. The seam is the same threshold the app governs; the dot is a unit of content resting *on the inside*, not yet crossed. The logo depicts the **moment** Decon governs — something waiting at the boundary — rather than claiming protection (which a lock or shield would over-promise). Restraint is the point, consistent with the rest of the product's careful under-claiming.

**Known weakness:** the mark encodes the *boundary* but not the *verb*. Decon's job is to **reduce** — many identifiers in, fewer out — and a single static dot doesn't show that. Three directions to fix it (client leans toward the first):

1. **Asymmetric density (recommended):** a small cluster of dots inside, one clean dot outside → `[ : | . ]`. Smallest change from current; converts the mark from a noun (*a boundary*) to a verb (*reducing across a boundary*).
2. **Pure threshold:** drop the dots; the seam becomes a gate/notch in a vertical line — maximally abstract, "systems tool," reads from a distance. Risk: too quiet, loses warmth.
3. **Redaction gesture:** a teal bar mid-slide across a stripe of text-marks. More literal, clearly "strips something," but trades away the preferred abstraction.

**To do:** render directions 1–3 as SVGs at favicon (16px), dock (~64px), and header (26px) sizes — legibility at small scale is the real test, and direction 1 should be validated there before committing.

---

## 13. Quality floor

- Responsive to mobile (panels and ledger stack at ≤840px; seam hidden).
- Visible keyboard focus on all controls (teal ring spec in §3).
- `prefers-reduced-motion` respected (§5).
- No `localStorage` / `sessionStorage` — in-memory state only.
- Clipboard writes wrapped defensively.

---

*Build to the mockup for layout and motion; build to this doc for intent. When the two ever disagree, the intent in §1 wins.*

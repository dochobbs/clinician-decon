# Bare name span hardening

**Date:** 2026-08-22

**Status:** implemented and tested locally

**Follows:** [Bare full-name span correction](2026-08-13-bare-full-name-span-fix.md) and commit
`0f5220f FIX: complete partially detected full names`

## Scope

A review pass over `0f5220f` found three weaknesses in the bare full-name completion rule:

1. The token pattern accepted any-case words, so a bare lowercase clinical phrase such as
   `chest pain` would be wholly masked to `[NAME]` if the model ever mislabeled one token as a
   name.
2. The rule matched exactly two tokens, so a three-token name paste (`mary jane watson`) with a
   partial detection still leaked the undetected tokens — the same defect class as the original
   incident, one arity up.
3. The composition logic lived in `local_rules.py`, blurring the boundary between deterministic
   rules and model-span composition.

## Correction

New module `package/src/decon/span_composition.py` owns model-span composition.
`complete_bare_name_spans` replaces `_complete_bare_name_span`, and
`local_rules._engine_extra_spans` imports it lazily to avoid a circular import.

Behavior changes:

- The bare-phrase match now accepts two or more alphabetic tokens covering the entire input,
  including particle surnames (`jean claude van damme`) and separately detected first/last tokens,
  which merge into one span.
- Expansion is skipped when any token is guarded vocabulary:
  - sentence guard (`has`, `reports`, `with`, ...) keeps sentence-shaped inputs untouched
    (`milo has asthma`),
  - clinical guard (symptoms, anatomy, spelled-out age units: `pain`, `fever`, `throat`,
    `month`, `old`, ...) keeps minimal clinical fragments from being wiped.

When expansion is skipped, only the model-tagged token is masked; the remaining text stays
visible for reviewer judgment instead of disappearing behind one `[NAME]`.

## Eval coverage

Pattern cases (completion must happen):

| Input | Detector returns | Expected |
| --- | --- | --- |
| `milo north` | `milo` | `[NAME]` (original regression case) |
| `mary jane watson` | `mary` | `[NAME]` |
| `Sofia Maria Reyes` | `Sofia` + `Reyes` separately | single merged span |
| `jean claude van damme` | `jean` | `[NAME]` |

Anti-pattern cases (useful info must survive):

| Input | Detector mislabels | Expected output |
| --- | --- | --- |
| `chest pain` | `pain` as name | `chest [NAME]` |
| `sore throat` | `sore` as name | `[NAME] throat` |
| `two month old` | `month` as name | `two [NAME] old` |
| `milo has asthma` | `milo` as name | `[NAME] has asthma` (control) |
| `liam needs refills` | `liam` as name | no expansion (unit test) |

## Verification

- Full package suite: 159 passed (151 prior + 8 new evals).
- README validation snapshot updated from `140 passed` to `159 passed`.

## Known trade-off

Guard lists are finite. A surname that collides with guarded vocabulary (for example a middle
name `May`) will not trigger whole-phrase expansion; the detected portion is still masked, and
the reviewer sees what remains. Over-masking remains recoverable by review; leaking is not.

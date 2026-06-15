# First-Name-Only Note Prose Audit

Date: 2026-06-15

## Trigger

A live-server note output preserved the patient first name `Marvin` throughout a de-identified
ADHD/anxiety follow-up note.

The missed pattern was ordinary clinical prose:

```text
Marvin is a patient who returns for follow-up...
Marvin reported...
Both Marvin and his mother...
```

The engine had strong coverage for names near obvious identifiers such as DOB, MRN, phone,
portal metadata, and section headers, but it did not propagate a first-name-only patient
identifier introduced by `Name is a patient...`.

## Root Cause

The local rules engine treated most name detection as local span matching. If a first name was
not directly matched at each occurrence, later standalone mentions were not removed.

This left gaps in common narrative note shapes:

- `Name is a patient who returns...`
- `Name returns for follow-up...`
- `Name presents...`
- `Name came in...`
- `Name's mother reports...`
- `Mother reports Name...`
- `The patient Name...`
- `Follow-up: Name had...`
- `Assessment: Name had...`

## Fix

Added patient-name propagation for first-name-only narrative introductions. Once a note introduces
a patient first name through one of the common note-prose patterns, later standalone uses of that
same name are removed.

The fix keeps an eponym guard so clinical terms such as `Wilson disease` are preserved when the
patient first name is also an eponym.

## Verification

Focused audit:

```text
15 common first-name-only note patterns
0 leaks after fix
```

Regression tests added:

- `test_decontextualize_text_removes_patient_first_name_introduced_in_note_prose`
- `test_decontextualize_text_preserves_eponym_when_patient_first_name_matches_condition`
- `test_decontextualize_text_removes_common_first_name_only_note_mentions`

Final verification:

```text
python3 -m pytest package/tests
97 passed

python3 package/scripts/run_validation.py
PASS: 1,000 source cases, 3,000 outputs, 0 PHI leaks, 0 missing clinical facts

python3 package/scripts/run_validation.py --suite persona-regression
PASS: 2,000 source cases, 6,000 outputs, 0 PHI leaks, 0 missing clinical facts
```

## Product Lesson

The synthetic suites had been too weighted toward labeled or adversarial PHI. A clinician note
can leak PHI through boring prose, not just through MRNs, DOBs, JSON, phone numbers, or prompt
injection. Future generator work should include a dedicated plain-note narrative archetype family.

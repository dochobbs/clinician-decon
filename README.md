# Clinician Decon

Clinician Decon is a local-first prototype for turning PHI-containing clinical text into a
reviewable, paste-ready prompt for tools such as ChatGPT, Gemini, Claude, OpenEvidence, or web
search.

The goal is simple: let a clinician paste from a PHI-protected workflow, remove or generalize
identifiers on their own machine, review the cleaned prompt, then copy it into a non-BAA tool
without sending raw PHI through this app.

Created on 2026-06-15 from the existing `Amboss/decon` package and later `cds-eval`
decontextualization research. The original source locations were copied, not moved.

## Current Prototype

The runnable app lives in `package/`.

```bash
cd /Users/dochobbs/Downloads/Consult/clinician-decon/package
PYTHONPATH=src python -m decon.app_server
```

Open:

```text
http://127.0.0.1:8769
```

Current behavior:

- local rules-based PHI minimization
- browser-based paste, decon, review, copy, and open workflow
- destination options for ChatGPT, Gemini, Claude, OpenEvidence, Web Search, and Copy Only
- no prompt text embedded in third-party URLs
- setup/model status endpoint for the future local model installer
- safe derived fields for common cases, such as DOB to age and `A1c 8.2` to `elevated A1c`

## Safety Model

V1 is local-first and fail-closed by default:

- Raw pasted text is processed on `127.0.0.1`.
- Removed PHI values are not shown in the audit panel, only categories.
- Third-party handoff is copy-to-clipboard plus opening the destination home page.
- Names, MRNs, phone numbers, email, SSNs, URLs, street addresses, and ZIP-level geography are
  removed or replaced with placeholders.
- Clinically useful facts may be preserved in safer form, such as age, coarse timing,
  generalized family relationships, or broad lab signals.

This prototype helps minimize PHI before using non-BAA tools. It does not replace legal review,
institutional policy, or clinician judgment.

## Verification

Run the package tests:

```bash
cd /Users/dochobbs/Downloads/Consult/clinician-decon/package
PYTHONPATH=src python -m pytest
```

Current local snapshot:

```text
34 passed
```

## Important Docs

- [Source map](SOURCE_MAP.md)
- [Mac local app design](docs/superpowers/specs/2026-06-15-mac-local-decon-app-design.md)
- [PHI field handling review](docs/superpowers/specs/2026-06-15-phi-field-handling-review.md)
- [Prototype implementation plan](docs/superpowers/plans/2026-06-15-local-decon-prototype.md)
- [Clinician tool brief](package/docs/clinician-decon-tool-brief.md)
- [Tabflows partner research](package/docs/tabflows-partner-research.md)

## Directory Layout

```text
clinician-decon/
  README.md
  SOURCE_MAP.md
  package/
    Standalone Python package copied from Amboss/decon.
  from-cds-eval/
    docs/
      Later local decon writeups and comparison reports.
    data/
      Synthetic and Amboss-derived decon test corpora.
    scripts/
      Evaluation and data-generation scripts from cds-eval.
    local_cds/
      Local regex + OpenMed NER implementation copied from cds-eval.
    eval/
      PHI stress/enriched fixtures copied from cds-eval/eval.
    results/decon_parity/
      Benchmark JSON outputs from local/Haiku parity runs.
  from-amboss/
    eval/
      Top-level Amboss PHI stress/enriched fixtures.
  workspace-notes/
    Consult workspace project note for decon.
```

## Highest-Value Starting Files

- `package/docs/clinician-decon-tool-brief.md`
- `package/docs/tabflows-partner-research.md`
- `package/src/decon/pipeline.py`
- `package/src/decon/service.py`
- `package/src/decon/tasks.py`
- `from-cds-eval/local_cds/decon.py`
- `from-cds-eval/docs/openmed_vs_haiku_decon_results.md`
- `from-cds-eval/docs/decon_combined_1132q_findings.md`
- `workspace-notes/decon.md`

## Current Recommendation

Use `package/` as the fork seed and promote the best parts of
`from-cds-eval/local_cds/decon.py` into the package:

1. Keep task-specific modes from `package/src/decon/tasks.py`.
2. Add the local regex + OpenMed NER pipeline as the default path.
3. Keep cloud LLM rewrite as an optional BAA-covered or explicitly enabled fallback.
4. Use the `from-cds-eval/data/` and `from-cds-eval/results/` artifacts as regression tests.

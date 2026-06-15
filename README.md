# Clinician Decon

Gathered working directory for the clinician-facing decontextualization tool.

Created on 2026-06-15 from the existing `Amboss/decon` standalone package and later
`cds-eval` decon research/evaluation work.

## What This Is For

This directory is the new staging area for turning the decon work into a simple clinician tool:

- paste PHI-containing chart/message/lab text from a protected workflow
- run local or BAA-covered PHI minimization
- produce a reviewed, paste-ready prompt for an external LLM or web/evidence tool
- preserve the lessons from Haiku, regex, OpenMed, multilingual, local, and hybrid approaches

The original source locations were copied, not moved. Originals remain in place.

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

## Runnable Prototype

The first local app prototype lives in `package/`.

```bash
cd /Users/dochobbs/Downloads/Consult/clinician-decon/package
PYTHONPATH=src python -m decon.app_server
```

Open `http://127.0.0.1:8769`.

Current prototype scope:

- local rules-based decon engine
- setup/model status endpoint
- PWA-style paste/decon/review screen
- ChatGPT, Gemini, Claude, OpenEvidence, Web Search, and Copy Only destinations
- copy-and-open handoff without putting prompt text in URLs

## Verification Snapshot

Before gathering, the standalone package tests passed in the original project:

```text
15 passed in 0.08s
```

After gathering, run tests from the copied package with:

```bash
cd /Users/dochobbs/Downloads/Consult/clinician-decon/package
python -m pytest -q
```

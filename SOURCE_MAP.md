# Source Map

This file records what was gathered into `clinician-decon` and where it came from.

## Copied From `Amboss/decon`

Destination: `package/`

Source:

```text
/Users/dochobbs/Downloads/Consult/Amboss/decon/
```

Copied contents:

- Python package: `src/decon/`
- tests: `tests/`
- package config: `pyproject.toml`
- README: `README.md`
- stress fixtures: `data/`
- original architecture/testing docs: `docs/`
- OpenAI evaluation reports: `reports/`

Excluded contents:

- `.git/`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `.DS_Store`

Important source branch at copy time:

```text
clinician-decon-tool
```

Known pre-existing untracked file preserved in the copy:

```text
reports/openai-gpt-5-mini-phi-suite-rerun.json
```

## Copied From `cds-eval`

Source:

```text
/Users/dochobbs/Downloads/Consult/cds-eval/
```

### Docs

Destination: `from-cds-eval/docs/`

- `docs/openmed_vs_haiku_decon_results.md`
- `docs/decon_combined_1132q_findings.md`
- `docs/decon_500q_results.md`
- `docs/decon_v3_regex_expansion_findings.md`
- `docs/HAIKU_DECONTEXTUALIZATION_ARCHITECTURE.md`
- `docs/PHI_DECONTEXTUALIZATION_TESTING.md`

### Data

Destination: `from-cds-eval/data/`

- `data/decon_amboss_stress.json`
- `data/decon_broad_queries.json`
- `data/decon_combined_1132.json`
- `data/decon_synth_500.json`
- `data/decon_synth_500_b.json`

### Scripts

Destination: `from-cds-eval/scripts/`

- `scripts/decon_broad_smoke.py`
- `scripts/decon_parity_test.py`
- `scripts/decon_three_way.py`
- `scripts/gen_decon_queries.py`
- `scripts/import_amboss_decon_data.py`
- `scripts/openmed_vs_haiku_decon.py`

### Local Implementation

Destination: `from-cds-eval/local_cds/`

- `eval/services/local_cds/decon.py`
- `eval/services/local_cds/__init__.py`

### Results

Destination: `from-cds-eval/results/decon_parity/`

- `results/decon_parity/broad_regex_ner_20260510_091159.json`
- `results/decon_parity/broad_regex_ner_20260510_091544.json`
- `results/decon_parity/broad_regex_ner_20260510_092325.json`
- `results/decon_parity/broad_regex_ner_20260510_092742.json`
- `results/decon_parity/broad_regex_ner_20260510_095429.json`
- `results/decon_parity/broad_regex_ner_20260510_111129.json`
- `results/decon_parity/broad_regex_ner_20260510_121625.json`
- `results/decon_parity/openmed_vs_haiku_20260510_085527.json`
- `results/decon_parity/openmed_vs_haiku_20260510_085739.json`
- `results/decon_parity/three_way_20260510_090447.json`

### Eval Fixtures

Destination: `from-cds-eval/eval/`

- `eval/phi_enriched_queries_20260406_081841.json`
- `eval/phi_stress_test.json`
- `eval/phi_stress_test_r2.json`
- `eval/phi_stress_test_r3.json`

## Copied From `Amboss`

Source:

```text
/Users/dochobbs/Downloads/Consult/Amboss/
```

### Eval Fixtures

Destination: `from-amboss/eval/`

- `eval/phi_enriched_queries_20260406_081841.json`
- `eval/phi_stress_test.json`
- `eval/phi_stress_test_r2.json`
- `eval/phi_stress_test_r3.json`

## Copied From `IronsVault`

Source:

```text
/Users/dochobbs/Downloads/Consult/IronsVault/Projects/decon.md
```

Destination:

```text
workspace-notes/decon.md
```

## Not Gathered Yet

These may still be worth checking later, but were not copied in this first pass:

- Broader `Amboss/docs/` historical reports outside `Amboss/decon/`.
- Broader `cds-eval/docs/2026-04-12-reports/` summary reports.
- `cds-eval-lab` presentation assets that describe decon in portfolio/product language.
- Any web app prototype code, because none exists yet in the decon package.

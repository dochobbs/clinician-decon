# Decon Workspace Note

## Summary

Clinician Decon is a local-first tool for turning PHI-containing clinical text into safer,
clinically useful prompts for external AI or search tools.

## Current Project Boundary

- App and package code live under `package/`.
- Validation suites live under `package/data/`.
- Historical synthetic fixtures live under `historical-fixtures/`.
- Release and QA docs live under `docs/qa/`.

## Useful Commands

```bash
cd package
python3 -m pytest
```

```bash
PYTHONPATH=package/src python3 package/scripts/run_validation.py --suite current
```

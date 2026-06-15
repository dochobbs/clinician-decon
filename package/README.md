# decon

Standalone project for the Haiku-based PHI decontextualization layer used to turn clinician free text into safe web-search queries.

## What is here

- A small Python package under `src/decon`
- A CLI for running decontextualization locally
- Regex-based PHI validation utilities
- Copied stress-test fixtures under `data/`
- Copied design/testing notes under `docs/`

## Install

```bash
cd decon
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Set `ANTHROPIC_API_KEY` before running the live model-backed decontextualizer.

## Run

```bash
decon "Marcus Johnson, DOB 3/15/2013, needs his 12-year-old vaccines per AAP"
```

With explicit patient context validation:

```bash
decon \
  --patient-context '{"name":"Marcus Johnson","mrn":"LP-2024-08432","dob":"2013-03-15"}' \
  "Marcus Johnson, DOB 3/15/2013, needs his 12-year-old vaccines per AAP"
```

## Test

```bash
pytest
```

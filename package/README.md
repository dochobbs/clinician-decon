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

## Run the local app prototype

From this directory:

```bash
PYTHONPATH=src python -m decon.app_server
```

Then open:

```text
http://127.0.0.1:8769
```

The prototype runs locally and uses the rules-based decon path. Destination buttons copy the
cleaned prompt and open the selected third-party site; prompt text is never placed in URLs.

## Test

```bash
pytest
```

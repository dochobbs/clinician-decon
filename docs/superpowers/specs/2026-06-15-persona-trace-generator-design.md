# Persona Trace Generator Design

Date: 2026-06-15

## Goal

Build a deterministic generator that turns the persona library plus clinical archetypes into
labeled decontextualization cases that can run through the existing headless validation gate.

## Inputs

- `package/data/personas/v1.json`: clinician, patient/context, source-channel, and perturbation
  personas.
- `package/data/archetypes/v1.json`: compact clinical archetypes with templated source text,
  PHI slots, required clinical facts, and allowed persona/perturbation tags.
- CLI options for count, seed, reference date, output path, and optional report path.

## Output

The generated case file uses the current `UsabilityCase` JSON shape so it can be loaded by
`decon.validation_runner` without a second evaluator:

```json
{
  "id": "P0001",
  "category": "persona_pediatric_vaccine",
  "query": "synthetic source text",
  "phi": ["synthetic identifier"],
  "forbidden_terms": [],
  "critical_facts": [
    {"label": "age", "acceptable_terms": ["10-year-old"]}
  ],
  "source_archetype": "pediatric-vaccine-catchup",
  "personas": {
    "clinician": "pediatric-vaccine-planner",
    "patient_context": "pediatric-catchup-vaccine-child",
    "source_channel": "portal-message-thread",
    "perturbations": ["relationship-noise"]
  },
  "slot_values": {"age": "10-year-old"},
  "seed": 20260615,
  "reference_date": "2026-06-15"
}
```

Extra metadata is retained in the file for traceability. The validator ignores fields it does
not need.

## Architecture

- `decon.persona_trace_generator`: loads JSON inputs, validates minimum structure, fills
  archetype slots with deterministic synthetic values, applies source-channel wrapping and
  perturbation noise, and writes case/report JSON.
- `package/scripts/generate_traces.py`: source-checkout wrapper for the module CLI.
- `decon.validation_runner`: registers the generated file as `persona-regression`, still using
  the existing clinical-usability suite path.

## Archetype Coverage

The first archetype set covers:

- pediatric vaccine catch-up
- weight-based dosing
- HLH/severe labs
- renal dose adjustment
- pregnancy medication safety
- asthma action plan
- allergy antibiotic alternative
- sibling multi-patient note
- portal callback triage
- rare disease web search

## Acceptance Criteria

- `python3 package/scripts/generate_traces.py --count 2000 --seed 20260615 --output package/data/decon_persona_regression_2000_2026-06-15.json --report package/reports/persona-regression-2000-2026-06-15.json`
  writes deterministic JSON.
- `decon-validate --suite persona-regression` and `python3 package/scripts/run_validation.py --suite persona-regression`
  work from a clone.
- The generated report records failure categories, PHI leak rate, clinical preservation rate,
  and persona/archetype breakdowns.
- Tests cover determinism, metadata, CLI generation, and validation-runner integration.

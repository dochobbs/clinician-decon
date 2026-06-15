# Persona Library

`v1.json` is the first durable synthetic persona library for Clinician Decon trace
generation.

It is intentionally structured as data rather than prose so a generator can combine:

- one clinician persona
- one patient/context persona
- one source-channel persona
- zero or more perturbation profiles

The generated trace should then record the selected persona IDs, filled PHI slots, required
clinical facts, perturbations, seed, and split. The personas are synthetic testing archetypes
only and must never contain real patient data.

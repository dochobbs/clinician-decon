# Archetype Library

`v1.json` contains clinician-reviewable clinical archetypes used by the persona-driven trace
generator.

Each archetype is a compact scenario with:

- a synthetic clinical template
- deterministic slot options
- PHI slots expected to be removed
- required clinical facts expected to survive decontextualization
- allowed clinician, patient/context, source-channel, and perturbation persona IDs

Generated suites keep the current validation case shape and add metadata such as selected
persona IDs, source archetype, slot values, seed, and reference date.

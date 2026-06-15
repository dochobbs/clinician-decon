# Persona Trace Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic persona-driven trace generator and register its generated suite in headless validation.

**Architecture:** Add versioned archetype JSON, a focused `decon.persona_trace_generator` module, a source-checkout CLI wrapper, and a `persona-regression` suite entry in `decon.validation_runner`. The generated case JSON keeps the existing usability validation shape plus metadata for persona/archetype traceability.

**Tech Stack:** Python stdlib, existing `decon.usability_eval` case schema, existing local validation runner.

---

### Task 1: Generator Contract Tests

**Files:**
- Create: `package/tests/test_persona_trace_generator.py`
- Modify: none

- [ ] **Step 1: Write failing tests**

Add tests that call `generate_persona_cases` and verify deterministic IDs, required metadata,
critical facts, PHI labels, and archetype coverage. Add a script-level test that writes output
and report JSON to `tmp_path`.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m pytest package/tests/test_persona_trace_generator.py
```

Expected: import failure for `decon.persona_trace_generator`.

### Task 2: Archetype Data And Generator

**Files:**
- Create: `package/data/archetypes/v1.json`
- Create: `package/data/archetypes/README.md`
- Create: `package/src/decon/persona_trace_generator.py`
- Create: `package/scripts/generate_traces.py`
- Modify: `package/pyproject.toml`

- [ ] **Step 1: Add archetype JSON**

Create ten archetypes covering pediatric vaccine catch-up, weight dosing, HLH/severe labs,
renal dosing, pregnancy meds, asthma action plan, allergy antibiotic choice, sibling notes,
portal callback, and rare disease web search.

- [ ] **Step 2: Implement generator**

Implement deterministic JSON loading, slot filling, source-channel wrappers, perturbation
application, case serialization, summary/report generation, and CLI parsing.

- [ ] **Step 3: Register console script**

Add `decon-generate-traces = "decon.persona_trace_generator:main"` to package scripts.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m pytest package/tests/test_persona_trace_generator.py
```

Expected: all tests pass.

### Task 3: Validation Integration

**Files:**
- Modify: `package/src/decon/validation_runner.py`
- Modify: `package/src/decon/validation_cli.py`
- Modify: `package/tests/test_validation_runner.py`

- [ ] **Step 1: Write failing validation test**

Assert `run_validation(suites=("persona-regression",), ...)` can run a small generated fixture
or the generated file once present, and assert CLI accepts `--suite persona-regression`.

- [ ] **Step 2: Wire suite**

Add `persona-regression` to `CURRENT_SUITES` pointing to
`package/data/decon_persona_regression_2000_2026-06-15.json`. `SUITE_CHOICES` should pick it up
from `CURRENT_SUITES`.

- [ ] **Step 3: Verify integration**

Run:

```bash
python3 -m pytest package/tests/test_validation_runner.py
```

Expected: all validation runner tests pass.

### Task 4: Generate Suite And Docs

**Files:**
- Create: `package/data/decon_persona_regression_2000_2026-06-15.json`
- Create: `package/reports/persona-regression-2000-2026-06-15.json`
- Create: `docs/qa/2026-06-15-persona-regression-2000-eval.md`
- Modify: `docs/qa/query-set-registry.md`
- Modify: `docs/qa/synthetic-trace-generation.md`
- Modify: `docs/qa/persona-library.md`
- Modify: `README.md`
- Modify: `package/README.md`

- [ ] **Step 1: Generate traces**

Run:

```bash
python3 package/scripts/generate_traces.py --count 2000 --seed 20260615 --output package/data/decon_persona_regression_2000_2026-06-15.json --report package/reports/persona-regression-2000-2026-06-15.json
```

- [ ] **Step 2: Run suite**

Run:

```bash
python3 package/scripts/run_validation.py --suite persona-regression --report package/reports/persona-regression-validation-2026-06-15.json
```

- [ ] **Step 3: Write QA report**

Save a markdown report with failure categories, PHI leak rate, clinical fact preservation rate,
and persona/archetype breakdowns.

- [ ] **Step 4: Update docs**

Link the new suite, generator command, and validation command from the registry and READMEs.

### Task 5: Final Verification

**Files:**
- All changed files

- [ ] **Step 1: Run tests**

```bash
python3 -m pytest package/tests
```

- [ ] **Step 2: Run current validation**

```bash
python3 package/scripts/run_validation.py
```

- [ ] **Step 3: Run persona validation**

```bash
python3 package/scripts/run_validation.py --suite persona-regression
```

- [ ] **Step 4: Check diff hygiene**

```bash
git diff --check
git status --short --branch
```

- [ ] **Step 5: Commit and push**

```bash
git add <changed files>
git commit -m "decon: add persona trace generator"
git push
```

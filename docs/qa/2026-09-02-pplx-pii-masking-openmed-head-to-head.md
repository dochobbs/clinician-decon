# PPLX PII Masking vs OpenMed Head-to-Head

Date: 2026-09-02

## Decision

Do not replace the current `rules+openmed` production mode with
`perplexity-ai/pplx-pii-masking`.

PPLX is a materially better balanced *raw detector* than OpenMed on Perplexity's
PII-TRACE benchmark, especially for repeated identifiers across turns. That result does not
transfer cleanly to Clinician Decon's product pipeline. On the frozen local release corpus,
`rules+openmed` retained a perfect product score while `rules+pplx` erased clinical facts in
221 source cases and leaked an EHR wrapper field in one. On the new
cross-turn stress set, PPLX reduced PII-recurrence leak cases from 10 to 3, but made 61
PII-recurrence cases unusable and damaged 20 clean sensitive-clinical controls.

Keep the adapter and comparison harness experimental. If multi-turn masking becomes a product
requirement, evaluate PPLX as a secondary conversation guard only after label-specific clinical
calibration and a substantially broader clinician-reviewed clean-negative set.

### Post-comparison hardening

The comparison below records the fair, pre-hardening model-to-model checkpoint. Follow-up work
kept OpenMed as the production semantic detector and improved the shared deterministic pipeline:

- residual identifiers improved from 19 / 36 to 36 / 36 handoff-usable outputs;
- OpenMed-backed cross-turn cases improved from 750 / 780 to 780 / 780;
- a new structured-boundary gate passed 432 / 432, including 48 matched PII-free controls; and
- the expanded release corpus passed 10,761 / 10,761 outputs across 3,587 source cases, with zero
  detected leaks and zero missing critical facts.

These results strengthen the hybrid recommendation. They do not retroactively change the raw
model comparison or establish completeness on unseen real-world data.

## What was compared

Both model arms were passed through the same deterministic Clinician Decon rules, span
composition, destination rendering, and evaluator:

- current arm: local rules plus
  [`OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1`](https://huggingface.co/OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1)
- candidate arm: local rules plus
  [`perplexity-ai/pplx-pii-masking`](https://huggingface.co/perplexity-ai/pplx-pii-masking)
- destinations: ChatGPT, Gemini, and web search
- release corpus: 3,171 source cases and 9,513 destination outputs, scored at the fixtures'
  frozen 2026-06-15 reference date
- cross-turn stress corpus: 260 source cases and 780 outputs, comprising 180 PII-recurrence
  dialogues and 80 clean clinical controls
- execution: CPU-only on the local machine; each detector received one warm-up call before
  latency measurement

All inputs are synthetic. Destination outputs from the same source case are correlated, so this
report gives both source-case and output counts rather than treating all outputs as independent.

## Results

### Frozen local release corpus

The first run accidentally used 2026-08-22 and made 11 age-band gold labels stale. Re-running
those 11 at their fixture date, 2026-06-15, restored OpenMed to 33 / 33 usable outputs; PPLX
retained 18 fact-loss outputs. The table combines the 3,160 unaffected cases with that corrected
11-case rerun. This fixes evaluator drift rather than hiding a model failure.

| Product pipeline | OpenMed | PPLX |
| --- | ---: | ---: |
| Source cases | 3,171 | 3,171 |
| Destination outputs | 9,513 | 9,513 |
| PHI-leak cases / outputs | 0 / 0 | 1 / 3 |
| Clinical-fact-loss cases / outputs | 0 / 0 | 221 / 663 |
| Handoff-usable outputs | 9,513 (100.0%) | 8,850 (93.0%) |
| Detector latency, mean | 101 ms | 402 ms |
| Detector latency, median | 104 ms | 312 ms |
| Detector latency, p95 | 121 ms | 1,089 ms |

PPLX's 221 fact-loss cases were spread across the corpus rather than confined to a single
fixture family: 108 persona-regression, 66 adversarial, 25 usability, 7 bare-name, 7 external
de-ID add-on, 5 clinician-seed, and 3 real-world cases.

The detector-only view also favored OpenMed on this local domain. OpenMed leaked expected PHI
in 771 / 3,171 cases and lost clinical facts in 628; PPLX leaked in 830 and lost facts in 806.
These deliberately harsh raw-detector metrics are not the product
gate—the deterministic layers close many misses—but they show that PPLX is not inherently a
better fit for this corpus.

### Cross-turn stress corpus

| Product pipeline | OpenMed | PPLX |
| --- | ---: | ---: |
| PII-recurrence cases | 180 | 180 |
| PII-recurrence leak cases / outputs | 10 / 30 | 3 / 9 |
| PII-recurrence fact-loss cases / outputs | 0 / 0 | 60 / 180 |
| PII-recurrence unusable outputs | 30 / 540 | 183 / 540 |
| Clean controls | 80 | 80 |
| Clean-control fact-loss cases / outputs | 0 / 0 | 20 / 60 |
| All handoff-usable outputs | 750 / 780 (96.2%) | 537 / 780 (68.8%) |
| Detector latency, mean | 238 ms | 1,036 ms |
| Detector latency, median | 171 ms | 411 ms |
| Detector latency, p95 | 668 ms | 6,230 ms |

OpenMed's 10 leak cases were concentrated in URL-embedded names (7), split name recurrence (2),
and an address dialogue (1). PPLX reduced those recurrence misses and detected all of the
repeated identifiers in dialogues with 45 intervening assistant lines. However, its broad
`other_pii` decisions removed:

- `eczema` in all 20 address dialogues;
- diagnoses and medications such as `asthma`, `budesonide`, `migraine with aura`, and
  `sumatriptan` in mixed and URL dialogues;
- `Adolescent transmasc` in all 20 otherwise PII-free sensitive-clinical controls.

PPLX's document sensitivity score did not separate the clean controls from PII-bearing cases:
the clean-control mean was 0.183 and the PII-recurrence mean was 0.191, with heavily overlapping
ranges. It should not be used as a simple product threshold without calibration evidence.

### Why the published benchmark looks different

Perplexity's PII-TRACE paper reports PPLX against raw OpenMed 434M on a 1,922-document synthetic
conversation test set. The paper's result is favorable to PPLX and should be taken seriously:

| PII-TRACE raw detector metric | OpenMed 434M | PPLX / PII-Tracer |
| --- | ---: | ---: |
| Character precision | 0.145 | 0.507 |
| Character recall | 0.919 | 0.830 |
| Character F1 | 0.251 | 0.629 |
| Consistent detection | 0.709 | 0.853 |
| Multi-mention consistent detection | 0.743 | 0.794 |
| Cross-turn consistent detection | 0.759 | 0.776 |
| PII-free false-positive rate, lower is better | 0.935 | 0.385 |

Source: [PII-TRACE paper](https://r2cdn.perplexity.ai/research/PII-Trace-202609.pdf), Tables 3 and 7.

Those are raw, label-agnostic model metrics under PII-TRACE's annotation policy. The local test
asks a different and product-specific question: what survives after a detector is composed with
Clinician Decon's deterministic removal and clinical-preservation policy? OpenMed's broad recall
is an asset in that layered design; PPLX's more contextual `other_pii` category conflicts with
the clinical facts this product must preserve.

## Important failure modes

1. **Clinical overmasking:** PPLX treats ordinary clinical content as `other_pii`. This is the
   dominant failure and cannot be fixed safely by dropping the label without a recall study.
2. **Span-composition interference:** in `RWA-001`, PPLX replaced `Male` on an EHR `Sex:` line.
   The partial replacement prevented the deterministic whole-line rule from removing the wrapper,
   leaving `Sex:` visible in all three destination outputs while also losing the sex fact.
3. **URL token fragmentation:** neither arm is perfect when a person's name is embedded in and
   later repeated outside a portal URL. PPLX improved the aggregate result but still leaked three
   URL-handle cases.
4. **CPU cost and long-tail latency:** PPLX was about 4x slower on the release set and 4.4x slower
   on the dialogue set, with a 6.2-second dialogue p95 on this machine.

## Candidate provenance

The experiment used a pinned local snapshot and the upstream Viterbi decoder:

- PPLX model revision: `1e6bb1edd41e03668c6931122be96df893141965`
- PPLX backbone code revision: `2c4d510dd4a732063c31a0f70193e35067b51fd8`
- `model.safetensors` SHA-256:
  `f6204155ec540c9323f706e284110ee848b462f0325dc1ece5c7263fc517bbd0`
- tokenizer compatibility flag: `fix_mistral_regex=true`

The upstream model card describes a roughly 0.6B-parameter bidirectional Qwen3 encoder with a
37-tag BIOES head over nine PII categories and a conversation sensitivity head. The local adapter
loads inspected, hash-pinned backbone code and strictly assigns the fine-tuned weights; it is not
registered as a supported Decon engine and does not change the current default.

## Reproduce

The comparison requires local model snapshots and a Python environment containing PyTorch,
Transformers, and Safetensors.

```bash
cd package
PYTHONPATH=src <model-python> scripts/compare_pii_models.py \
  --suite release \
  --reference-date 2026-06-15 \
  --pplx-fix-mistral-regex \
  --report reports/pplx-openmed-release-2026-09-02.json

PYTHONPATH=src <model-python> scripts/compare_pii_models.py \
  --suite conversation-repeat \
  --reference-date 2026-06-15 \
  --pplx-fix-mistral-regex \
  --report reports/pplx-openmed-conversation-repeat-2026-09-02.json
```

Generated JSON under `package/reports/` is intentionally ignored. The reproducible code,
deterministic cross-turn cases, tests, and this decision record are the durable artifacts.

The later residual-identifier add-on is documented separately in
`docs/qa/2026-09-02-residual-identifier-redteam.md`. It was added to the `release` registry after
this 3,171-case comparison, so reproducing `--suite release` from the newer registry also runs
those 12 cases.

## Verification state

- Candidate adapter and conversation-suite tests: 3 passed.
- Full package suite after hybrid hardening: 181 passed in 806.53 seconds.
- Focused production-style gate: 416 source cases, 1,248 outputs, zero leaks, zero missing facts,
  and 100% handoff usability.
- Expanded cached-detector release gate: 3,587 source cases, 10,761 product outputs, zero leaks,
  zero missing facts, and 100% handoff usability.
- `git diff --check`: passed.

## Limits and next experiment

- PII-TRACE is vendor-authored, and its underlying dataset was not publicly listed on Hugging
  Face when checked on 2026-09-02, so its numbers could not be independently reproduced here.
- The local corpora are synthetic and contain repeated templates; counts measure regression
  surface coverage, not real-world prevalence or statistical independence.
- The current cross-turn set is now a release regression gate but remains narrow: 20 synthetic
  identities across 13 fixed dialogue shapes. It still needs clinician-reviewed paraphrases, more
  languages, more long-window boundaries, and true PII-free conversational negatives.
- CPU latency does not predict Apple Silicon MPS or production accelerator performance.

The next justified experiment is external validation: add at least 250 clinician-reviewed clean
clinical conversations and blinded adversarial cases, then re-run without changing rules against
the test set. Do not change the production default unless a candidate preserves the current
zero-leak, zero-fact-loss release result and improves independent evidence.

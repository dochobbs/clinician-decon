# Philter-UCSF Head-To-Head

Date: 2026-06-16

## Source

Cloned repository:

```text
/Users/dochobbs/Downloads/Consult/philter-ucsf
```

Upstream:

```text
https://github.com/BCHSI/philter-ucsf
```

Checked commit:

```text
4da3cf3 Merge pull request #10 from paulheider/patch-filepath-creation
```

## What Philter Is

Philter-UCSF is a command-line clinical note de-identification tool. Its default mode processes
plain text files and outputs either tagged XML or asterisk-masked text. It is designed around broad
clinical-note de-identification, not LLM prompt handoff.

The default `philter_delta.json` config contains:

- `304` regex filters
- `5` regex-context filters
- `3` set/dictionary filters
- `1` POS matcher
- no enabled Stanford NER filters in this config

## Setup Findings

Philter did not run out of the box on the current machine.

Required local setup:

```bash
cd /Users/dochobbs/Downloads/Consult/philter-ucsf
python3 -m venv .venv
.venv/bin/python -m pip install -i https://pypi.org/simple \
  'chardet>=5' 'nltk>=3.8' 'numpy>=2' 'pandas>=2' 'xmltodict>=0.13' setuptools
.venv/bin/python - <<'PY'
import nltk
nltk.download('averaged_perceptron_tagger_eng')
PY
```

Compatibility issues found:

- The checked-in dependency pins are old: `numpy==1.22.0`, `pandas==1.0.5`, `nltk==3.6.6`.
- Python 3.14 no longer provides `distutils`, so `setuptools` is needed for the compatibility
  shim.
- `160` regex filters use old inline `(?i)` placement such as `\b(?i)...`, which Python 3.13+
  rejects with `global flags not at the start`.

For this benchmark, the local clone was patched in `philter.py` so `precompile()` removes embedded
`(?i)` tokens and compiles with `re.IGNORECASE`. No upstream files were copied into Clinician
Decon.

## Test Method

Two datasets were used:

1. `package/data/decon_clinician_seed_gold_10_2026-06-16.json`
2. Current gate:
   - `package/data/decon_usability_500_2026-06-15.json`
   - `package/data/decon_adversarial_500_2026-06-15.json`
3. Philter-adversarial add-on:
   - `package/data/decon_philter_adversarial_addon_50_2026-06-16.json`

For Philter, each query was written to a `.txt` file and processed with:

```bash
.venv/bin/python main.py \
  -i /private/tmp/decon-philter-compare/current_input \
  -o /private/tmp/decon-philter-compare/current_output \
  -f ./configs/philter_delta.json \
  --prod=True \
  --outputformat asterisk
```

For Clinician Decon, each query was processed with:

```text
decontextualize_text(..., destination="chatgpt", engine="rules+openmed")
```

Both outputs were scored using the same case labels:

- `forbidden_terms` / `phi` must not remain in output.
- each `critical_facts` label must retain at least one acceptable term.

This is a product-fit benchmark, not a formal Philter i2b2 benchmark. It intentionally tests
clinician prompt handoff needs: PHI removal plus preservation or generalization of clinically
necessary facts.

## Results

| Dataset | Tool | Safe cases | PHI-leaked cases | Clinically usable cases | Missing-critical-fact cases |
| --- | --- | ---: | ---: | ---: | ---: |
| Seed-gold 10 | Philter-UCSF | `5 / 10` | `5 / 10` | `6 / 10` | `4 / 10` |
| Seed-gold 10 | Clinician Decon `rules+openmed` | `10 / 10` | `0 / 10` | `10 / 10` | `0 / 10` |
| Original current 1,000 | Philter-UCSF | `759 / 1,000` | `241 / 1,000` | `399 / 1,000` | `601 / 1,000` |
| Original current 1,000 | Clinician Decon `rules+openmed` | `1,000 / 1,000` | `0 / 1,000` | `1,000 / 1,000` | `0 / 1,000` |
| Philter-adversarial add-on 50 | Philter-UCSF | `31 / 50` | `19 / 50` | `35 / 50` | `15 / 50` |
| Philter-adversarial add-on 50 | Clinician Decon `rules+openmed` | `50 / 50` | `0 / 50` | `50 / 50` | `0 / 50` |

Timing notes:

- Philter processed the original 1,000 current files in about `6.4 s` wall-clock in one CLI run after setup.
- Clinician Decon processed the same original 1,000 cases through `rules+openmed` in `92.38 s`, about
  `92.38 ms/case`, including local OpenMed inference.
- On the 50-case add-on, Philter ran in `0.931 s` and Clinician Decon `rules+openmed` ran in
  `8.333 s`; see `docs/qa/2026-06-16-philter-adversarial-addon-head-to-head.md`.

## Representative Philter Failures

### GOLD-001

Input issue:

- Spelled-out phone number was preserved.
- DOB was masked instead of converted to age.

Philter output excerpt:

```text
Mom says that ****** had anxiety worse on methylphenidate. DOB * ** ****.
Callback is five one two five five five zero one four seven.
Needs ADHD med alternative before **** **** **.
```

Impact:

- PHI leak: spelled-out phone.
- Clinical utility loss: expected `13-year-old`.

### GOLD-003

Input issue:

- Clinical eponym collision: `Addison disease` was masked as if `Addison` were only a name.

Philter output excerpt:

```text
Endocrine note: ******* disease on hydrocortisone, vomiting today.
```

Impact:

- No PHI leak in this case.
- Clinical utility loss: disease name removed.

### GOLD-006

Input issue:

- `mychart.local` and `yesterday` remained.

Philter output excerpt:

```text
mychart.local/patient/***-****/MRN-**-****-***** says fever 104.2 at 2am.
Dad says *** is 18 months, under-immunized, no wet diapers since yesterday.
```

Impact:

- PHI/workflow leak: patient portal host.
- Date leak: relative date.
- Clinical facts mostly retained.

### GOLD-010

Input issue:

- `A1c 8.2` and `BMI 31` remained as forbidden exact values in this prompt-handoff rubric.
- DOB was masked, but no age was derived.

Philter output excerpt:

```text
Patient had A1c 8.2, BMI 31, started metformin; mom asks about vomiting.
```

Impact:

- PHI/prompt-policy leak under our exact-value generalization rule.
- Clinical utility loss: no `13-year-old`, no `elevated A1c`, no `obesity-range BMI`.

## Interpretation

Philter is impressive for its original target: clinical note de-identification with a conservative
asterisk mask and a large hand-built rule bank. It is not a drop-in replacement for our clinician
LLM handoff pipeline.

Main differences:

- Philter masks; Clinician Decon decontextualizes and generalizes.
- Philter assumes anything not explicitly included can become asterisks; our pipeline tries to
  retain clinically meaningful context.
- Philter does not derive age from DOB, generalize exact labs/body measurements, or render
  destination-specific LLM prompts.
- Philter's default config catches many classic note PHI patterns, but misses prompt-handoff
  cases we care about: spelled-out phone numbers, portal hostnames, relative dates, room fragments,
  and exact clinical values that need safe generalization.
- Philter is much faster per file once running, but it has a heavier modern install-maintenance
  burden because of old dependency pins, NLTK data, and Python regex compatibility issues.

## What We Should Reuse

Useful ideas from Philter:

- Its large regex taxonomy is worth mining, especially:
  - address/location variants
  - date variants
  - MRN/account/accession/order/serial patterns
  - note-style safe-word lists
  - context regexes for names
- Its coordinate-map architecture is useful for auditability: every span can be tied back to the
  filter that created or protected it.
- Its asterisk output is useful as a debugging mode, but not as the clinician-facing output.

What not to copy directly:

- Do not replace our pipeline with Philter.
- Do not adopt a default asterisk-mask UX for LLM handoff.
- Do not inherit its dependency pins or runtime assumptions without modernization.

## Recommendation

Keep Clinician Decon's pipeline:

```text
deterministic rules
  -> OpenMed PHI-NER
  -> residual risk scan
  -> optional reviewer/fallback for hard cases
```

Use Philter as a pattern library and adversarial-test source, not as the product engine. The
highest-value follow-up is to mine Philter's regex categories into candidate tests, then port only
the patterns that improve our failure set without damaging clinical fact preservation.

# External De-ID Adversarial Add-On Head-To-Head

Date: 2026-06-16

## Purpose

This pass adds 50 synthetic cases designed to stress Clinician Decon with patterns that a broad
de-identification tool like external de-ID baseline might plausibly handle well:

- accession, specimen, voiceprint, passport, license, military, claim, group, UUID, and device IDs
- HL7, FHIR, JSON, file-name, QR, portal-token, and chat-export shapes
- full addresses, ZIP+4, facility unit/bed, school bus route, and rare-organization references
- Unicode names, German month dates, Spanish family prose, and phone-number words
- clinical eponyms and name/drug collisions where over-masking can damage usefulness
- prompt-injection and uniqueness phrases that should be removed before LLM handoff

The suite lives at:

```text
package/data/decon_external_deid_adversarial_addon_50_2026-06-16.json
```

## Commands

Clinician Decon validation:

```bash
PYTHONPATH=package/src python3 package/scripts/run_validation.py \
  --suite external-deid-adversarial-addon \
  --reference-date 2026-06-16
```

Head-to-head scoring used a local OpenMed-capable Python and a temporary comparison harness:

```bash
PYTHONPATH=package/src /path/to/python-with-transformers \
  /tmp/decon_baseline_addon_compare.py \
  --repo clinician-decon \
  --suite clinician-decon/package/data/decon_external_deid_adversarial_addon_50_2026-06-16.json \
  --baseline /path/to/external-deid-baseline \
  --python /path/to/python-with-transformers \
  --output /tmp/decon-baseline-addon-report.json
```

external de-ID baseline was run from the local clone at:

```text
/path/to/external-deid-baseline
```

using:

```bash
.venv/bin/python main.py \
  -i /tmp/decon-baseline-addon-*/input \
  -o /tmp/decon-baseline-addon-*/output \
  -f ./configs/baseline_config.json \
  --prod=True \
  --outputformat asterisk
```

## Results

| Dataset | Tool | Safe cases | PHI-leaked cases | Clinically usable cases | Missing-critical-fact cases | Handoff usable |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Add-on 50 | external de-ID baseline | `31 / 50` | `19 / 50` | `35 / 50` | `15 / 50` | `22 / 50` |
| Add-on 50 | Clinician Decon `rules+openmed` | `50 / 50` | `0 / 50` | `50 / 50` | `0 / 50` | `50 / 50` |

Destination validation for Clinician Decon:

- Source cases: `50`
- Destination outputs: `150`
- PHI-leaked outputs: `0 / 150`
- Unsafe copy-allowed leaks: `0 / 150`
- Clinically usable outputs: `150 / 150`
- Handoff usable outputs: `150 / 150`
- Max average runtime in local-rules validation: `0.509 ms`
- Max p95 runtime in local-rules validation: `0.597 ms`

Head-to-head runtime:

- external de-ID baseline: `0.931 s` for 50 files in one CLI run
- Clinician Decon `rules+openmed`: `8.333 s` for 50 cases in the comparison runner

The Decon timing includes local OpenMed inference. No network call was used.

## Did The External De-ID Baseline Do Better?

On the final current pipeline, no. The external de-ID baseline did not beat Clinician Decon on any labeled safety or
clinical-usability metric in this add-on set.

The external de-ID baseline did handle 22 cases cleanly and usefully, especially structured or classic patterns such as
radiology accession, IPv6/MAC metadata, device serials, certificate numbers, military ID, ACH
payment identifiers, full addresses, ISO datetimes, HL7/FHIR, UUIDs, base64-ish portal tokens,
dictation signatures, spaced MRNs, embedded file names, smartwatch serials, and court-order IDs.

The main external de-ID baseline advantage remains speed after setup. The main product gap remains that it masks
text; it does not decontextualize for a clinician-to-LLM handoff.

## Representative external de-ID baseline Misses

| Case | Failure | Sample impact |
| --- | --- | --- |
| `PHF-002` fax extension | leaked `ext 4421`; did not generalize `TSH 8.1` | a local callback extension remained and the lab fact was not converted to `elevated TSH` |
| `PHF-007` voiceprint ID | leaked `VP-88A1` | biometric/workflow identifier remained |
| `PHF-011` passport travel | leaked `next month` | relative travel date remained in an otherwise useful output |
| `PHF-012` driver license STI | over-masked `doxyPEP` and `condomless exposure` | safety was mostly OK, but the STI guidance question became less usable |
| `PHF-017` facility unit/bed | leaked `unit 4E` and `bed 12`; over-masked age prefix | facility-local routing identifiers remained |
| `PHF-019` Addison disease | masked `Addison disease` | classic eponym collision damaged the clinical condition |
| `PHF-023` email alias | leaked nickname `Peanut`; masked `SMART` | identity nickname remained and asthma-treatment option was damaged |
| `PHF-026` Spanish prose | masked `ED` in `necesita ED?` | Spanish family/location text was aggressively masked and triage meaning was damaged |
| `PHF-027` OCR identifiers | leaked spaced MRN and spaced phone | OCR-style identifier shapes were preserved |
| `PHF-030` JSON chart | preserved exact `A1c 8.2` and `BMI 31` | prompt-handoff rubric requires safe generalization, not raw exact values |
| `PHF-040` uniqueness/facility | leaked uniqueness, floor, facility, and relative date | `Only HLH patient on 7th floor east at Children's today` remained mostly intact |
| `PHF-049` Pax/Paxlovid collision | masked `Paxlovid` and `COVID` | name-like drug collision harmed medication and diagnosis facts |
| `PHF-050` prompt injection | leaked `ADMIN OVERRIDE` and workstation serial | prompt-injection text and workstation identifier remained |

## Pipeline Hardening From This Set

The add-on suite produced useful fixes in Clinician Decon:

- added the suite as a real validation gate, not only a registered dataset
- added coverage for more identifier classes: biometric, certificate, trial, court, workstation,
  QR, portal token, group, routing, UUID, credit card, MAC, IPv6, and file-name patterns
- expanded location/address handling for facilities, rehab/institute names, unit/bed/floor,
  bus-route stops, ZIP+4, Spanish street labels, and non-comma city/state formats
- expanded name handling for URL query names, JSON/HL7/QR names, nickname labels, Spanish caregiver
  reports, leading identifier labels, patient-name labels without punctuation, and signature blocks
- added German month date parsing so DOB dates still become age bands
- changed contextual uniqueness replacement so `Only HLH patient` preserves the clinical condition as
  `Rare HLH case` while removing the re-identification cue
- made web-search query shaping fall back to de-identified clinical context for travel-medicine and
  vaccine-reaction questions instead of emitting an overly generic immunization search

## Current Status

The add-on suite is now part of `CURRENT_SUITES` as `external-deid-adversarial-addon`, and the package test
suite includes a regression test requiring:

- `50 / 50` source cases
- `150 / 150` destination outputs
- `0` PHI-leaked outputs
- `0` missing-critical-fact outputs
- `100%` clinical usability
- `100%` handoff usability

"""Compare OpenMed PHI-NER masking vs cloud rewrite LLM-rewrite decon.

Uses the same 10 synthetic-PHI clinical queries as decon_parity_test.
Two structurally different approaches, scored on the same axes:

  - OpenMed: token-classification → mask detected spans inline.
  - cloud rewrite: BRIGHTLINE_ROUTER_PROMPT → rewrite query as a clinical
    question (the production pipeline).

Both produce a "PHI-free version" of the query. We score:

  - PHI leakage (any input identifier surviving in the output)
  - JSON validity (cloud rewrite only — OpenMed's output is plain text)
  - Latency (model load excluded)
  - Output character length

Usage:
  python3 scripts/local_model_decon_decon.py
  python3 scripts/local_model_decon_decon.py --skip-cloud-rewrite  # NER only
  python3 scripts/local_model_decon_decon.py --model OpenMed/...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, ROOT)

# Reuse the same test queries as the gemma-vs-cloud_rewrite parity test
from scripts.decon_parity_test import (  # noqa: E402
  TEST_QUERIES, BRIGHTLINE_ROUTER_PROMPT, build_user_prompt,
  cloud_rewrite_route, _parse_json,
)

DEFAULT_OPENMED = "OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1"
OUT_DIR = f"{ROOT}/results/decon_parity"


def load_openmed(model_id: str):
  """Load the OpenMed PHI-NER model via transformers pipeline.

  Returns a callable: text -> list of {entity_group, score, word, start, end}.
  """
  from transformers import pipeline
  print(f"Loading {model_id}…", flush=True)
  t0 = time.perf_counter()
  ner = pipeline(
    "token-classification",
    model=model_id,
    aggregation_strategy="simple",
    device=-1,  # CPU; the model is small and Ollama owns the GPU
  )
  print(f"  loaded in {time.perf_counter() - t0:.1f}s", flush=True)
  return ner


def openmed_mask(ner, text: str) -> dict:
  """Run NER, build masked output, return spans + timing."""
  t0 = time.perf_counter()
  spans = ner(text)
  latency = time.perf_counter() - t0
  # Sort by start descending so replacements don't shift indices
  spans_sorted = sorted(spans, key=lambda s: s["start"], reverse=True)
  masked = text
  for s in spans_sorted:
    label = s["entity_group"]
    masked = masked[: s["start"]] + f"[{label}]" + masked[s["end"] :]
  return {
    "masked": masked,
    "spans": [
      {"label": s["entity_group"], "text": s["word"],
       "start": s["start"], "end": s["end"], "score": float(s["score"])}
      for s in spans
    ],
    "latency_s": latency,
  }


def check_phi_in_text(text: str, phi_terms: list[str]) -> list[str]:
  """Return PHI terms that survived in the output."""
  if not text:
    return []
  return [t for t in phi_terms if t and t.lower() in text.lower()]


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--model", default=DEFAULT_OPENMED)
  ap.add_argument("--skip-cloud-rewrite", action="store_true")
  args = ap.parse_args()

  ner = load_openmed(args.model)

  print()
  print(f"OpenMed vs cloud rewrite decon  |  n={len(TEST_QUERIES)}")
  print("=" * 80)

  results = []
  for tq in TEST_QUERIES:
    qid = tq["id"]
    print(f"\n=== {qid}: {tq['query'][:65]}{'…' if len(tq['query'])>65 else ''} ===")
    age = tq["demographics"]["age"]
    sex = tq["demographics"]["sex"]
    row = {"id": qid, "query": tq["query"], "phi_terms": tq["phi_terms"],
           "demographics": tq["demographics"]}

    # OpenMed masking
    om = openmed_mask(ner, tq["query"])
    om_leaks = check_phi_in_text(om["masked"], tq["phi_terms"])
    om["leaks"] = om_leaks
    print(f"  openmed  {om['latency_s']*1000:6.0f}ms  "
          f"spans={len(om['spans']):2d}  leaks={len(om_leaks)}")
    print(f"           masked: {om['masked']}")
    if om["spans"]:
      span_str = " | ".join(f"{s['label']}:{s['text']}" for s in om["spans"])
      print(f"           spans:  {span_str}")
    row["openmed"] = om

    # cloud rewrite route
    if not args.skip_cloud_rewrite:
      try:
        h = cloud_rewrite_route(tq["query"], age, sex)
        cds = (h.get("parsed") or {}).get("cds_query") or ""
        chart = (h.get("parsed") or {}).get("chart_instructions") or ""
        h["leaks_in_cds"] = check_phi_in_text(cds, tq["phi_terms"])
        h["leaks_in_chart"] = check_phi_in_text(chart, tq["phi_terms"])
        leaks_total = len(h["leaks_in_cds"]) + len(h["leaks_in_chart"])
        print(f"  cloud_rewrite    {h['latency_s']*1000:6.0f}ms  "
              f"valid_json={h.get('parsed') is not None}  "
              f"leaks={leaks_total}")
        if cds:
          print(f"           cds: {cds[:90]}{'…' if len(cds)>90 else ''}")
        row["cloud_rewrite"] = h
      except Exception as e:
        print(f"  cloud_rewrite    ERROR {e}")
        row["cloud_rewrite"] = {"error": str(e)}

    results.append(row)

  # Summary
  print("\n" + "=" * 80)
  print("PARITY SUMMARY")
  print("=" * 80)

  om_rows = [r for r in results if "openmed" in r]
  om_total_leaks = sum(len(r["openmed"]["leaks"]) for r in om_rows)
  om_avg_lat_ms = sum(r["openmed"]["latency_s"] for r in om_rows) / len(om_rows) * 1000
  om_total_spans = sum(len(r["openmed"]["spans"]) for r in om_rows)
  om_total_phi_terms = sum(len(r["phi_terms"]) for r in om_rows)
  print(f"  openmed  n={len(om_rows):2d}  spans={om_total_spans:3d}  "
        f"phi_terms_in_input={om_total_phi_terms:3d}  "
        f"leaks={om_total_leaks}  avg_lat={om_avg_lat_ms:.0f}ms")

  if not args.skip_cloud_rewrite:
    h_rows = [r for r in results if r.get("cloud_rewrite") and not r["cloud_rewrite"].get("error")]
    if h_rows:
      h_total_leaks = sum(
        len(r["cloud_rewrite"].get("leaks_in_cds", [])) +
        len(r["cloud_rewrite"].get("leaks_in_chart", []))
        for r in h_rows)
      h_avg_lat_ms = sum(r["cloud_rewrite"]["latency_s"] for r in h_rows) / len(h_rows) * 1000
      h_valid = sum(1 for r in h_rows if r["cloud_rewrite"].get("parsed") is not None)
      print(f"  cloud_rewrite    n={len(h_rows):2d}  valid_json={h_valid}/{len(h_rows)}  "
            f"leaks={h_total_leaks}  avg_lat={h_avg_lat_ms:.0f}ms")

  Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  out = f"{OUT_DIR}/local_model_decon_{ts}.json"
  with open(out, "w") as fh:
    json.dump({"timestamp": ts, "openmed_model": args.model,
               "results": results}, fh, indent=2)
  print(f"\n→ {out}")


if __name__ == "__main__":
  main()

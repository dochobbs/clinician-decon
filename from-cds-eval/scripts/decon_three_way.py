"""Three-way decon comparison: OpenMed (NER+regex) vs gemma4:e4b vs Haiku.

  - **OpenMed** uses eval.services.local_cds.decon.OpenMedDecon, which now
    applies a regex pre-filter before the NER pass. Both layers are CPU /
    fully local, deterministic.
  - **gemma4:e4b** uses Ollama with the production BRIGHTLINE_ROUTER_PROMPT
    — fully local, LLM-based rewrite.
  - **Haiku** is the cloud reference (Anthropic API). Skipped by default
    when --skip-haiku is set.

Same 10 synthetic-PHI clinical queries as decon_parity_test.

Scoring:
  - PHI leakage: any input identifier surviving in the output
  - Latency
  - For LLM rewriters (gemma + Haiku): JSON validity + needs_cds match
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = "/Users/dochobbs/Downloads/Consult/cds-eval"
sys.path.insert(0, ROOT)

from eval.services.local_cds.decon import OpenMedDecon, FALLBACK_MODEL  # noqa: E402
from scripts.decon_parity_test import (  # noqa: E402
  TEST_QUERIES, gemma_route, haiku_route, build_user_prompt, _parse_json,
)

OUT_DIR = f"{ROOT}/results/decon_parity"


def check_phi(text: str, phi_terms: list[str]) -> list[str]:
  if not text:
    return []
  return [t for t in phi_terms if t and t.lower() in text.lower()]


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--openmed-model", default=FALLBACK_MODEL,
                  help="OpenMed PHI-NER model id (transformers-loadable)")
  ap.add_argument("--gemma-host", default="http://localhost:11434")
  ap.add_argument("--gemma-model", default="gemma4:e4b")
  ap.add_argument("--skip-haiku", action="store_true",
                  help="Skip the Haiku cloud comparison (fully local mode)")
  args = ap.parse_args()

  decon = OpenMedDecon(args.openmed_model)

  print(f"Three-way decon parity")
  print(f"  openmed: {args.openmed_model} (regex+NER)")
  print(f"  gemma:   {args.gemma_model} @ {args.gemma_host}")
  print(f"  haiku:   {'skipped' if args.skip_haiku else 'cloud reference'}")
  print(f"  n: {len(TEST_QUERIES)}")
  print("=" * 80)

  results = []
  for tq in TEST_QUERIES:
    qid = tq["id"]
    print(f"\n=== {qid}: {tq['query'][:65]}{'…' if len(tq['query'])>65 else ''} ===")
    age = tq["demographics"]["age"]
    sex = tq["demographics"]["sex"]
    row = {"id": qid, "query": tq["query"], "phi_terms": tq["phi_terms"]}

    # OpenMed (regex + NER)
    om = decon.mask(tq["query"])
    om_leaks = check_phi(om.masked, tq["phi_terms"])
    print(f"  openmed  {om.latency_s*1000:6.0f}ms  spans={len(om.spans):2d}  "
          f"leaks={len(om_leaks)}")
    print(f"           masked: {om.masked}")
    if om.spans:
      span_str = " | ".join(f"{s.label}:{s.text}" for s in om.spans[:8])
      print(f"           spans:  {span_str}")
    row["openmed"] = {
      "masked": om.masked,
      "spans": [s.__dict__ for s in om.spans],
      "leaks": om_leaks,
      "latency_s": om.latency_s,
    }

    # gemma4
    try:
      g = gemma_route(args.gemma_host, args.gemma_model, tq["query"], age, sex)
      cds = (g.get("parsed") or {}).get("cds_query") or ""
      chart = (g.get("parsed") or {}).get("chart_instructions") or ""
      g_leaks = check_phi(cds, tq["phi_terms"]) + check_phi(chart, tq["phi_terms"])
      needs = (g.get("parsed") or {}).get("needs_cds")
      print(f"  gemma    {g['latency_s']*1000:6.0f}ms  valid_json={g.get('parsed') is not None}  "
            f"leaks={len(g_leaks)}  needs_cds={needs}")
      if cds:
        print(f"           cds: {cds[:90]}{'…' if len(cds)>90 else ''}")
      g["leaks"] = g_leaks
      row["gemma"] = g
    except Exception as e:
      print(f"  gemma    ERROR {e}")
      row["gemma"] = {"error": str(e)}

    # Haiku (optional)
    if not args.skip_haiku:
      try:
        h = haiku_route(tq["query"], age, sex)
        cds = (h.get("parsed") or {}).get("cds_query") or ""
        chart = (h.get("parsed") or {}).get("chart_instructions") or ""
        h_leaks = check_phi(cds, tq["phi_terms"]) + check_phi(chart, tq["phi_terms"])
        print(f"  haiku    {h['latency_s']*1000:6.0f}ms  valid_json={h.get('parsed') is not None}  "
              f"leaks={len(h_leaks)}")
        if cds:
          print(f"           cds: {cds[:90]}{'…' if len(cds)>90 else ''}")
        h["leaks"] = h_leaks
        row["haiku"] = h
      except Exception as e:
        print(f"  haiku    ERROR {e}")
        row["haiku"] = {"error": str(e)}

    results.append(row)

  # Summary
  print("\n" + "=" * 80)
  print("THREE-WAY PARITY SUMMARY")
  print("=" * 80)

  def summarize(name: str, key: str, leak_field: str = "leaks"):
    rows = [r for r in results if key in r and not r[key].get("error")]
    if not rows:
      print(f"  {name:8s}  (no rows)")
      return
    leaks = sum(len(r[key].get(leak_field, [])) for r in rows)
    avg_lat = sum(r[key]["latency_s"] for r in rows) / len(rows) * 1000
    extra = ""
    if name in ("gemma", "haiku"):
      valid = sum(1 for r in rows if r[key].get("parsed") is not None)
      extra = f"  valid_json={valid}/{len(rows)}"
    print(f"  {name:8s}  n={len(rows):2d}  leaks={leaks}{extra}  avg_lat={avg_lat:.0f}ms")

  total_phi_in_input = sum(len(r["phi_terms"]) for r in results)
  print(f"  total PHI terms in input: {total_phi_in_input}")
  summarize("openmed", "openmed")
  summarize("gemma", "gemma")
  if not args.skip_haiku:
    summarize("haiku", "haiku")

  Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  out = f"{OUT_DIR}/three_way_{ts}.json"
  with open(out, "w") as fh:
    json.dump({"timestamp": ts, "openmed_model": args.openmed_model,
               "gemma_model": args.gemma_model,
               "results": results}, fh, indent=2)
  print(f"\n→ {out}")


if __name__ == "__main__":
  main()

"""Decontextualization parity test: gemma4:e4b vs cloud rewrite.

Same BRIGHTLINE_ROUTER_PROMPT as production. Runs each sample query
through both, checks:

  - PHI leakage: any patient identifier from the input surviving in
    cds_query (name, MRN, DOB, age-as-DOB, etc.)
  - Structural parity: both return valid JSON with cds_query +
    chart_instructions + needs_cds
  - Routing parity: both produce the same needs_cds verdict
  - Latency

Usage:
  python3 scripts/decon_parity_test.py
  python3 scripts/decon_parity_test.py --gemma-host http://localhost:11434
  python3 scripts/decon_parity_test.py --skip-cloud-rewrite  # gemma only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, ROOT)

# Reuse the production prompt verbatim
from clinical_insights_websearch import BRIGHTLINE_ROUTER_PROMPT  # noqa: E402

DEFAULT_GEMMA_HOST = "http://localhost:11434"
DEFAULT_GEMMA_MODEL = "gemma4:e4b"
CLOUD_REWRITE_MODEL = "cloud-rewrite-reference"
OUT_DIR = f"{ROOT}/results/decon_parity"

# 10 clinical queries with synthetic PHI for parity testing
TEST_QUERIES = [
  {
    "id": "Q01",
    "query": "Sarah Johnson (DOB 2014-03-15, MRN LP-08432) needs her vaccines, what's due?",
    "demographics": {"age": 12, "sex": "F"},
    "phi_terms": ["Sarah", "Johnson", "2014-03-15", "LP-08432"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q02",
    "query": "Pt John Doe 67M on lisinopril 20mg, BP 138/85 today, up the dose?",
    "demographics": {"age": 67, "sex": "M"},
    "phi_terms": ["John", "Doe"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q03",
    "query": "Marcus Chen, DOB 1988-11-04, A1c 7.9 last month — what's next step?",
    "demographics": {"age": 37, "sex": "M"},
    "phi_terms": ["Marcus", "Chen", "1988-11-04"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q04",
    "query": "12yo Emma Park due for HPV, when do we start the series?",
    "demographics": {"age": 12, "sex": "F"},
    "phi_terms": ["Emma", "Park"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q05",
    "query": "Newborn boy of pt Mary Brown (DOB 1990-05-22), fever 39.2C at 6 weeks, manage?",
    "demographics": {"age": 0, "sex": "M"},
    "phi_terms": ["Mary", "Brown", "1990-05-22"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q06",
    "query": "65F Linda Wong w/ new dx breast CA, what tamoxifen dose for ER+?",
    "demographics": {"age": 65, "sex": "F"},
    "phi_terms": ["Linda", "Wong"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q07",
    "query": "CKD3 pt age 72, MRN 555-1234 on metformin — should I dc?",
    "demographics": {"age": 72, "sex": "M"},
    "phi_terms": ["555-1234"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q08",
    "query": "When do we start statins per USPSTF?",
    "demographics": {"age": 50, "sex": "M"},
    "phi_terms": [],
    "expected_needs_cds": True,
  },
  {
    "id": "Q09",
    "query": "Mr. Davis (60yoM) had +UA today, anything to do if asymptomatic?",
    "demographics": {"age": 60, "sex": "M"},
    "phi_terms": ["Davis"],
    "expected_needs_cds": True,
  },
  {
    "id": "Q10",
    "query": "When was the last visit?",
    "demographics": {"age": 45, "sex": "F"},
    "phi_terms": [],
    "expected_needs_cds": False,
  },
]


def build_user_prompt(query: str, age: int | None, sex: str | None) -> str:
  demo = []
  if age is not None:
    demo.append(f"{age} year old")
  if sex:
    demo.append("male" if sex == "M" else "female")
  demo_str = ", ".join(demo) if demo else "unknown"
  return f"Query: {query}\nPatient: {demo_str}"


def gemma_route(host: str, model: str, query: str,
                age: int | None, sex: str | None) -> dict:
  user_prompt = build_user_prompt(query, age, sex)
  payload = json.dumps({
    "model": model,
    "messages": [
      {"role": "system", "content": BRIGHTLINE_ROUTER_PROMPT},
      {"role": "user", "content": user_prompt},
    ],
    "temperature": 0.0,
    "max_tokens": 512,
    "options": {"num_ctx": 8192},
  }).encode()
  req = urllib.request.Request(
    f"{host}/v1/chat/completions",
    data=payload, headers={"Content-Type": "application/json"})
  t0 = time.perf_counter()
  with urllib.request.urlopen(req, timeout=120) as resp:
    body = json.loads(resp.read())
  latency = time.perf_counter() - t0
  text = body["choices"][0]["message"]["content"].strip()
  return {"raw": text, "latency_s": latency,
          "parsed": _parse_json(text)}


def cloud_rewrite_route(query: str, age: int | None, sex: str | None) -> dict:
  from anthropic import Anthropic
  client = Anthropic()
  user_prompt = build_user_prompt(query, age, sex)
  t0 = time.perf_counter()
  resp = client.messages.create(
    model=CLOUD_REWRITE_MODEL,
    max_tokens=512,
    system=BRIGHTLINE_ROUTER_PROMPT,
    messages=[{"role": "user", "content": user_prompt}],
  )
  latency = time.perf_counter() - t0
  text = resp.content[0].text.strip()
  return {"raw": text, "latency_s": latency,
          "parsed": _parse_json(text)}


def _parse_json(text: str) -> dict | None:
  candidates = []
  if "```json" in text:
    candidates.append(text.split("```json", 1)[1].split("```", 1)[0].strip())
  elif "```" in text:
    candidates.append(text.split("```", 1)[1].split("```", 1)[0].strip())
  candidates.append(text.strip())
  for c in candidates:
    try:
      return json.loads(c)
    except (json.JSONDecodeError, ValueError):
      continue
  return None


def check_phi(parsed: dict | None, phi_terms: list[str]) -> dict:
  """Return list of PHI leaks found in cds_query and chart_instructions."""
  if not parsed:
    return {"leaks": [], "valid": False}
  leaks = []
  for field in ("cds_query", "chart_instructions"):
    val = parsed.get(field) or ""
    for term in phi_terms:
      # Case-insensitive substring match for names/identifiers
      if term and term.lower() in val.lower():
        leaks.append({"field": field, "term": term})
  return {"leaks": leaks, "valid": True}


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--gemma-host", default=DEFAULT_GEMMA_HOST)
  ap.add_argument("--gemma-model", default=DEFAULT_GEMMA_MODEL)
  ap.add_argument("--skip-cloud-rewrite", action="store_true")
  ap.add_argument("--skip-gemma", action="store_true")
  args = ap.parse_args()

  print(f"Decon parity test: gemma={args.gemma_model} vs cloud_rewrite={CLOUD_REWRITE_MODEL}")
  print(f"Test queries: {len(TEST_QUERIES)}")
  print()

  results = []
  for tq in TEST_QUERIES:
    print(f"=== {tq['id']}: {tq['query'][:60]}{'…' if len(tq['query'])>60 else ''} ===")
    age = tq["demographics"]["age"]
    sex = tq["demographics"]["sex"]
    row = {"id": tq["id"], "query": tq["query"],
           "demographics": tq["demographics"],
           "phi_terms": tq["phi_terms"],
           "expected_needs_cds": tq["expected_needs_cds"]}

    if not args.skip_gemma:
      try:
        g = gemma_route(args.gemma_host, args.gemma_model, tq["query"], age, sex)
        g["phi"] = check_phi(g.get("parsed"), tq["phi_terms"])
        leaks = len(g["phi"]["leaks"])
        cds = (g.get("parsed") or {}).get("cds_query")
        needs = (g.get("parsed") or {}).get("needs_cds")
        print(f"  gemma:    {g['latency_s']:5.2f}s  leaks={leaks}  needs_cds={needs}")
        if cds: print(f"            cds: {cds[:90]}{'…' if cds and len(cds)>90 else ''}")
        row["gemma"] = g
      except Exception as e:
        print(f"  gemma:    ERROR {e}")
        row["gemma"] = {"error": str(e)}

    if not args.skip_cloud_rewrite:
      try:
        h = cloud_rewrite_route(tq["query"], age, sex)
        h["phi"] = check_phi(h.get("parsed"), tq["phi_terms"])
        leaks = len(h["phi"]["leaks"])
        cds = (h.get("parsed") or {}).get("cds_query")
        needs = (h.get("parsed") or {}).get("needs_cds")
        print(f"  cloud_rewrite:    {h['latency_s']:5.2f}s  leaks={leaks}  needs_cds={needs}")
        if cds: print(f"            cds: {cds[:90]}{'…' if cds and len(cds)>90 else ''}")
        row["cloud_rewrite"] = h
      except Exception as e:
        print(f"  cloud_rewrite:    ERROR {e}")
        row["cloud_rewrite"] = {"error": str(e)}

    results.append(row)
    print()

  print("=" * 70)
  print("PARITY SUMMARY")
  print("=" * 70)
  def summarize(name, key):
    rows = [r for r in results if r.get(key) and not r[key].get("error")]
    if not rows: return
    valid = [r for r in rows if r[key].get("phi", {}).get("valid")]
    leaks = sum(len(r[key].get("phi", {}).get("leaks", [])) for r in rows)
    needs_match = sum(1 for r in rows
                      if (r[key].get("parsed") or {}).get("needs_cds") == r["expected_needs_cds"])
    avg_lat = sum(r[key]["latency_s"] for r in rows) / len(rows)
    print(f"  {name:8s}  n={len(rows):2d}  valid_json={len(valid):2d}/{len(rows)}  "
          f"phi_leaks={leaks}  needs_cds_match={needs_match}/{len(rows)}  "
          f"avg_lat={avg_lat:.2f}s")

  summarize("gemma", "gemma")
  summarize("cloud_rewrite", "cloud_rewrite")

  Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  out = f"{OUT_DIR}/decon_parity_{ts}.json"
  with open(out, "w") as fh:
    json.dump({"timestamp": ts, "gemma_model": args.gemma_model,
               "cloud_rewrite_model": CLOUD_REWRITE_MODEL, "results": results}, fh, indent=2)
  print(f"\n→ {out}")


if __name__ == "__main__":
  main()

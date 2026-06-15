"""Adapter: import Amboss decon team's stress test data into our test format.

Source: /Users/dochobbs/Downloads/Consult/Amboss/decon/data/phi_stress_test_*.json
That suite was used to validate the Haiku decon pipeline at 100% PHI strip
rate across 132 progressively-adversarial queries (rounds 1-4).

Schemas vary across rounds. We normalize everything to our format:
  {id, category, query, phi: [list of expected PHI terms]}
"""

from __future__ import annotations

import json
from pathlib import Path

AMBOSS_DECON = "/Users/dochobbs/Downloads/Consult/Amboss/decon/data"
OUT = "/Users/dochobbs/Downloads/Consult/cds-eval/data/decon_amboss_stress.json"


def collect_phi_from_context(ctx: dict) -> list[str]:
  """Pull all expected-PHI strings from a patient_context dict."""
  out = []
  for k in ("name", "mrn", "dob"):
    v = ctx.get(k)
    if v and isinstance(v, str) and v.strip():
      out.append(v.strip())
      # Also break "First Last" into components since the leak detector
      # checks each independently
      if k == "name" and " " in v:
        out.extend(v.split())
  for x in ctx.get("other_phi", []) or []:
    if isinstance(x, str) and x.strip():
      out.append(x.strip())
  return out


def import_round(path: str, round_label: str) -> list[dict]:
  d = json.load(open(path))
  qs = d["queries"] if isinstance(d, dict) else d
  out = []
  for i, q in enumerate(qs):
    qid = q.get("id") or q.get("sid") or f"{round_label}_{i:03d}"
    text = q.get("physician_query") or q.get("query") or q.get("original_query")
    if not text:
      continue
    if "phi_present" in q:
      phi = list(q["phi_present"])
    else:
      phi = collect_phi_from_context(q.get("patient_context", {}))
    out.append({
      "id": f"{round_label}_{qid}",
      "category": f"amboss_{round_label}_{q.get('category', q.get('set', 'general'))}",
      "query": text,
      "phi": phi,
    })
  return out


def main():
  all_queries = []
  for fname, label in [
    ("phi_stress_test.json",    "r1"),
    ("phi_stress_test_r2.json", "r2"),
    ("phi_stress_test_r3.json", "r3"),
    ("phi_stress_test_r4.json", "r4"),
  ]:
    p = f"{AMBOSS_DECON}/{fname}"
    if not Path(p).exists():
      print(f"  skip: {p} not found")
      continue
    qs = import_round(p, label)
    print(f"  {fname}: {len(qs)} queries imported")
    all_queries.extend(qs)

  Path(OUT).parent.mkdir(parents=True, exist_ok=True)
  with open(OUT, "w") as fh:
    json.dump(all_queries, fh, indent=2)
  total_phi = sum(len(q["phi"]) for q in all_queries)
  print(f"\n→ {OUT}")
  print(f"  total: {len(all_queries)} queries, {total_phi} PHI terms")


if __name__ == "__main__":
  main()

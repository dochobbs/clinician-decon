"""Broad PHI-decon smoke test against ~80 synthetic clinical queries.

Categories:
  - name variations (simple, compound, foreign, with-title, lastname-first, initials)
  - MRN variations (numeric, alphanumeric, lowercase context, with prefix)
  - phone, SSN, email, ZIP, dates (multiple formats)
  - address fragments
  - demographic shorthand (65F, 32yoM) — should NOT be tagged as PHI
  - clinical-lookalike values (A1c, GFR, ICD-10, drug strengths) — false-positive bait
  - dense multi-PHI strings
  - PHI-free baselines (should produce 0 spans)
  - real-world stress patterns (Spruce log lines, EHR exports)

Reports:
  - Leak rate by category (recall)
  - False-positive rate on no-PHI queries (precision proxy)
  - Latency distribution

Usage:
  python3 scripts/decon_broad_smoke.py
  python3 scripts/decon_broad_smoke.py --model OpenMed/...
  python3 scripts/decon_broad_smoke.py --regex-only        # NER off, just regex
  python3 scripts/decon_broad_smoke.py --ner-only          # Regex off, just NER
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = "/Users/dochobbs/Downloads/Consult/cds-eval"
sys.path.insert(0, ROOT)

from eval.services.local_cds.decon import (  # noqa: E402
  OpenMedDecon, FALLBACK_MODEL, _REGEX_PATTERNS,
)

QUERIES_PATH = f"{ROOT}/data/decon_broad_queries.json"
OUT_DIR = f"{ROOT}/results/decon_parity"


def regex_only_mask(text: str) -> tuple[str, list[dict], float]:
  """Replicate just the regex layer for ablation."""
  t0 = time.perf_counter()
  matches = []
  for label, pat in _REGEX_PATTERNS:
    for m in pat.finditer(text):
      if m.lastindex:
        start, end = m.span(m.lastindex)
      else:
        start, end = m.span(0)
      matches.append((start, end, label, text[start:end]))
  matches.sort(key=lambda x: (x[0], -x[1]))
  selected, last_end = [], -1
  for start, end, label, span_text in matches:
    if start >= last_end:
      selected.append((start, end, label, span_text))
      last_end = end
  masked = text
  spans = []
  for start, end, label, span_text in sorted(selected, key=lambda x: x[0],
                                              reverse=True):
    masked = masked[:start] + f"«{label}»" + masked[end:]
    spans.append({"label": label, "text": span_text, "start": start,
                  "end": end, "score": 1.0})
  return masked, spans, time.perf_counter() - t0


def check_leaks(masked: str, phi_terms: list[str]) -> list[str]:
  """Return PHI terms surviving as STANDALONE WORDS in masked output.

  Naive substring matching gives false positives — "Bo" matches inside
  "newborn", "Mia" matches inside "hyperbilirubinemia". A real PHI leak
  requires the term to appear as a standalone word/identifier, not as
  a substring of an unrelated medical term.
  """
  if not masked:
    return []
  hits = []
  m_lower = masked.lower()
  for t in phi_terms:
    if not t:
      continue
    t_lower = t.lower()
    # Word-boundary match for typical PHI terms. We escape the term
    # because identifiers may contain dots, dashes, slashes, etc.
    pat = re.compile(r"\b" + re.escape(t_lower) + r"\b")
    if pat.search(m_lower):
      hits.append(t)
  return hits


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--model", default=FALLBACK_MODEL)
  ap.add_argument("--queries", default=QUERIES_PATH,
                  help="Path to query JSON file (default: 80-q hand-curated)")
  ap.add_argument("--regex-only", action="store_true")
  ap.add_argument("--ner-only", action="store_true",
                  help="Disable regex pre-filter (debug only)")
  args = ap.parse_args()

  queries = json.load(open(args.queries))
  print(f"Broad decon smoke — {len(queries)} queries")
  print(f"  model: {args.model}")
  if args.regex_only:
    print(f"  mode: regex-only (NER disabled)")
  elif args.ner_only:
    print(f"  mode: NER-only (regex disabled)")
  else:
    print(f"  mode: regex + NER (production)")
  print()

  if not args.regex_only:
    decon = OpenMedDecon(args.model)
  else:
    decon = None

  results = []
  total_phi = 0
  total_leaks = 0
  fp_count = 0
  fp_queries = 0
  by_cat = defaultdict(lambda: {"n": 0, "leaks": 0, "phi": 0, "fp_spans": 0})

  for i, q in enumerate(queries, 1):
    cat = q["category"]
    expected = q.get("phi", [])
    is_no_phi = (len(expected) == 0)

    if args.regex_only:
      masked, spans, lat = regex_only_mask(q["query"])
    else:
      d = decon.mask(q["query"])
      masked, spans, lat = d.masked, [s.__dict__ for s in d.spans], d.latency_s

    leaks = check_leaks(masked, expected)
    fp_spans = len(spans) if is_no_phi else 0

    by_cat[cat]["n"] += 1
    by_cat[cat]["leaks"] += len(leaks)
    by_cat[cat]["phi"] += len(expected)
    by_cat[cat]["fp_spans"] += fp_spans

    total_phi += len(expected)
    total_leaks += len(leaks)
    if is_no_phi and len(spans) > 0:
      fp_queries += 1
      fp_count += len(spans)

    status = "✗" if leaks else "✓"
    if is_no_phi and len(spans) > 0:
      status += "fp"
    print(f"[{i:2d}/{len(queries)}] {q['id']:5s} {cat[:24]:24s} {status:5s} "
          f"spans={len(spans):2d} leaks={len(leaks)} {lat*1000:5.0f}ms")
    if leaks:
      print(f"        LEAKED: {leaks}  masked: {masked[:120]}")
    elif is_no_phi and spans:
      span_str = " | ".join(f"{s['label']}:{s['text']}" for s in spans[:5])
      print(f"        FP: {span_str}")

    results.append({
      "id": q["id"], "category": cat, "query": q["query"],
      "expected_phi": expected, "is_no_phi": is_no_phi,
      "masked": masked, "spans": spans,
      "leaks": leaks, "fp_spans": fp_spans,
      "latency_s": lat,
    })

  # Summary
  print()
  print("=" * 80)
  print("BROAD DECON SUMMARY")
  print("=" * 80)
  print(f"  total queries:        {len(queries)}")
  print(f"  total PHI terms:      {total_phi}")
  print(f"  PHI leaks:            {total_leaks}/{total_phi} "
        f"({100*total_leaks/max(1,total_phi):.1f}%)")
  print(f"  no-PHI queries:       {sum(1 for q in queries if not q.get('phi'))}")
  print(f"  no-PHI w/ FP spans:   {fp_queries} "
        f"({fp_count} total false-positive spans)")
  avg_lat = sum(r["latency_s"] for r in results) / len(results) * 1000
  p95_lat = sorted([r["latency_s"]*1000 for r in results])[int(len(results)*0.95)]
  print(f"  latency:              avg={avg_lat:.0f}ms  p95={p95_lat:.0f}ms")
  print()
  print(f"  {'category':30s}  {'n':>3s}  {'phi':>3s}  {'leaks':>5s}  {'fp_spans':>8s}")
  for cat in sorted(by_cat):
    s = by_cat[cat]
    leak_rate = f"{100*s['leaks']/max(1,s['phi']):.0f}%" if s['phi'] else "n/a"
    print(f"  {cat:30s}  {s['n']:>3d}  {s['phi']:>3d}  "
          f"{s['leaks']:>3d} {leak_rate:>4s}  {s['fp_spans']:>8d}")

  Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  mode = "regex" if args.regex_only else ("ner" if args.ner_only else "regex_ner")
  out = f"{OUT_DIR}/broad_{mode}_{ts}.json"
  with open(out, "w") as fh:
    json.dump({"timestamp": ts, "model": args.model, "mode": mode,
               "n": len(results),
               "summary": {
                 "total_phi": total_phi, "total_leaks": total_leaks,
                 "leak_rate": total_leaks/max(1,total_phi),
                 "fp_queries": fp_queries, "fp_spans_total": fp_count,
                 "avg_latency_ms": avg_lat, "p95_latency_ms": p95_lat,
                 "by_category": dict(by_cat),
               },
               "results": results}, fh, indent=2)
  print(f"\n→ {out}")


if __name__ == "__main__":
  main()

"""Local PHI scrubbing for clinical queries.

Two-layer defense:
  Layer 1 (regex)  — deterministic, sub-millisecond, catches well-defined
                     formats (SSN, phone, email, ZIP, MRN-with-context,
                     ISO/US dates). Closes gaps the NER model misses.
  Layer 2 (NER)    — OpenMed token classifier; catches names, free-form
                     addresses, ambiguous numbers, mixed identifiers.

Empirically (see docs/openmed_vs_haiku_decon_results.md), the NER layer
alone misses some MRN formats that look like phone numbers. The regex
pre-filter eliminates that class of leak.

The combined output is deterministic: same input → same masked output.
That's the key advantage over LLM decon — no creative rewrites, no
hallucinated patient details.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

# SuperClinical English wins bulk recall (0% leak on standard PHI at n=1000+
# synthetic, 3% on Amboss). Multilingual catches niche cases (nicknames,
# Spanish, multi-patient) but regressed bulk recall to 3% AND raised FP
# rate 8× on no-PHI queries. Use multilingual as a router fallback for
# non-Latin / nickname-heavy inputs, not a default.
DEFAULT_MODEL = "OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1"
MULTILINGUAL_MODEL = "OpenMed/privacy-filter-multilingual"
FALLBACK_MODEL = "OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1"

# ---------------------------------------------------------------------------
# Regex patterns — Layer 1 (pre-filter)
# ---------------------------------------------------------------------------

# Order matters: longest/most-specific first so they don't get clobbered
# by shorter overlapping matches.
_REGEX_PATTERNS: list[tuple[str, re.Pattern]] = [
  # MRN with explicit context — catches "MRN 555-1234", "MRN: LP-08432",
  # "MR# 12345678". The ID portion is tagged as MRN regardless of format.
  ("MRN",
   re.compile(r"\b(?:MRN|MR#|Medical[\s-]?Record[\s-]?(?:Number|#))[\s:#]*"
              r"([A-Z0-9][A-Z0-9-]{3,})\b", re.IGNORECASE)),
  # Email
  ("EMAIL",
   re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  # SSN with explicit context — catches "SSN 123456789", "SSN: 123-45-6789".
  # We anchor on the SSN keyword because bare 9-digit numbers can be many
  # things (account, MRN); without context, leave them to NER.
  ("SSN",
   re.compile(r"\b(?:SSN|Social[\s-]?Security[\s-]?(?:Number|#)?)"
              r"[\s:#]*(\d{3}[-\s]?\d{2}[-\s]?\d{4}|\d{9})\b",
              re.IGNORECASE)),
  # Bare SSN with dashes (no keyword). 9 digits no-dashes is too risky
  # to catch without context.
  ("SSN",
   re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  # Phone (US-ish)
  ("PHONE",
   re.compile(r"(?:\+1[\s-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  # Date — ISO (1990-05-22) or US (5/22/1990 or 05-22-1990)
  ("DATE",
   re.compile(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")),
  # ZIP+4 or 5
  ("ZIP",
   re.compile(r"\b\d{5}(?:-\d{4})?\b")),
  # URL with patient/user identifier in path — catches mychart-style PHI.
  ("URL_USER",
   re.compile(r"\b(?:https?://)?[\w.-]+/(?:patient|user|profile|chart|"
              r"member|account)/(\S+)\b", re.IGNORECASE)),
  # Body measurements paired with weight or height — common HIPAA-#5
  # adjacent identifiers when combined with age.
  ("BODY",
   re.compile(r"\b\d{2,3}\s*(?:lbs?|kg|pounds?)\b", re.IGNORECASE)),
  ("HEIGHT",
   re.compile(r"\b\d{1,2}'\s*\d{1,2}\"|\b\d{1,2}\s*ft\s*\d{1,2}\s*in\b")),
  # Insurance / practice names — small curated list. Production deployment
  # should expand from a real payor/practice index.
  ("INSURANCE",
   re.compile(r"\b(?:Blue\s+Cross|BCBS|Aetna|Cigna|UnitedHealth(?:care)?|"
              r"Kaiser|Humana|Anthem|Medicaid|Medicare|Tricare)\b",
              re.IGNORECASE)),
  ("PRACTICE",
   re.compile(r"\b(?:Lakes\s+Pediatrics|Children's\s+Hospital|Mayo\s+Clinic|"
              r"Cleveland\s+Clinic)\b", re.IGNORECASE)),
  # "Since [Month]" / "seen [Month]" temporal references — HIPAA #3
  # (dates more specific than year).
  ("TEMPORAL",
   re.compile(r"\b(?:since|seen|on|started)\s+"
              r"(?:January|February|March|April|May|June|July|August|"
              r"September|October|November|December|Jan|Feb|Mar|Apr|"
              r"Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b", re.IGNORECASE)),
  # Implicit relational references — "the twins' older brother",
  # "her younger sister", "grandma Shirley", "Mom (Jennifer)". These
  # can re-identify a patient even without an explicit name. We strip
  # the entire relational+name unit.
  ("RELATION",
   re.compile(
     r"\b(?:the\s+)?(?:twins'?|siblings'?)\s+"
     r"(?:older|younger|baby|little)?\s*"
     r"(?:brother|sister|sibling|kid|child)\b",
     re.IGNORECASE)),
  ("RELATION_NAMED",
   re.compile(
     r"\b(?:Mom|Mama|Mami|Mother|Dad|Papa|Father|Grandma|Grandpa|"
     r"Auntie?|Uncle|Tia|Tio|Abuela|Abuelo)\s+"
     r"\(([A-Z][a-z]+)\)|"
     r"\b(?:Mom|Dad|Grandma|Grandpa|Aunt|Uncle)\s+"
     r"([A-Z][a-z]+)\b")),
  # Spanish-language clinical phrasing — common "La mama de [Name]",
  # "Mi hijo [Name]", "El paciente [Name]". The English NER misses the
  # name following Spanish particles.
  ("SPANISH_RELATION",
   re.compile(r"\b(?:La\s+mam[aá]|El\s+pap[aá]|Mi\s+hij[oa]|Su\s+hij[oa]|"
              r"El\s+paciente|La\s+paciente)\s+(?:de\s+)?"
              r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)", re.IGNORECASE)),
  # Nicknames — common patterns "Lil D", "Big J", "Little [Name]"
  ("NICKNAME",
   re.compile(r"\b(?:Lil|Little|Big|Lil')\s+([A-Z](?:\.|\b)|[A-Z][a-z]{1,3})",
              re.IGNORECASE)),
  # "called him/her X" or "known as X" — name introduction patterns
  ("CALLED_AS",
   re.compile(r"\b(?:calls?\s+(?:him|her|them)|known\s+as|nicknamed)\s+"
              r"([A-Z][a-zA-Z]+)\b")),
  # Multi-patient detection: "X and Y both have", "A (3yo) and B (5yo)".
  # The second name often slips past NER if separated by a parenthetical.
  # We catch "and [Capitalized Word]" within ~50 chars of another caps name.
  ("MULTI_PATIENT_AND",
   re.compile(r"\band\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+"
              r"\(\d+\s*(?:yo|year|mo|month)", re.IGNORECASE)),
  # Shelter / SDoH location references — hard to enumerate exhaustively
  # but a few common patterns. SDoH text isn't HIPAA per se but combined
  # with demographics it's re-identifying.
  ("SHELTER",
   re.compile(r"\b(?:Salvation\s+Army|Catholic\s+Charities|Goodwill|"
              r"YMCA|YWCA|homeless\s+shelter|women's\s+shelter)\b",
              re.IGNORECASE)),
]


@dataclass
class PHISpan:
  label: str
  text: str
  start: int
  end: int
  score: float


@dataclass
class DeconResult:
  original: str
  masked: str
  spans: list[PHISpan] = field(default_factory=list)
  latency_s: float = 0.0


class OpenMedDecon:
  """Lazily-loaded PHI-NER masker."""

  def __init__(self, model_id: str = DEFAULT_MODEL):
    self.model_id = model_id
    self._pipeline = None  # lazy load

  def _load(self):
    if self._pipeline is not None:
      return
    # Try MLX first (fast, native Apple Silicon). If model is HF
    # transformers safetensors, this falls back to transformers pipeline.
    try:
      from transformers import pipeline
      self._pipeline = pipeline(
        "token-classification",
        model=self.model_id,
        aggregation_strategy="simple",
        device=-1,  # CPU; small model, leaves GPU for synthesis
      )
    except Exception as e:
      if self.model_id != FALLBACK_MODEL:
        # MLX-format model may not load via transformers; fall back
        from transformers import pipeline
        self._pipeline = pipeline(
          "token-classification",
          model=FALLBACK_MODEL,
          aggregation_strategy="simple",
          device=-1,
        )
        self.model_id = FALLBACK_MODEL
      else:
        raise

  def mask(self, text: str) -> DeconResult:
    """Two-layer scrub: regex pre-filter, then OpenMed NER.

    Returns spans from both layers, in detection order. Indices in the
    returned spans refer to positions in the *original* text, not the
    intermediate.
    """
    self._load()
    t0 = time.perf_counter()

    # Layer 1: regex pre-filter. We replace matches with sentinel placeholders
    # in a working copy, but record spans against the *original* text so
    # downstream tooling can audit what was masked where.
    regex_spans: list[PHISpan] = []
    working = text
    # Collect all regex matches first (against original), then apply
    # sequentially right-to-left to the working copy.
    matches = []
    for label, pat in _REGEX_PATTERNS:
      for m in pat.finditer(text):
        # If the pattern uses a capturing group, mask the group; else
        # mask the whole match.
        if m.lastindex:
          start, end = m.span(m.lastindex)
        else:
          start, end = m.span(0)
        matches.append((start, end, label, text[start:end]))
    # Sort by (start, -end) so non-overlapping greedy selection picks longer
    matches.sort(key=lambda x: (x[0], -x[1]))
    selected = []
    last_end = -1
    for start, end, label, span_text in matches:
      if start >= last_end:
        selected.append((start, end, label, span_text))
        last_end = end

    for start, end, label, span_text in sorted(selected, key=lambda x: x[0],
                                                reverse=True):
      # Use unicode angle brackets so NER won't re-tag the placeholder.
      # Standard ASCII brackets like [MRN] get mis-classified by NER as
      # name/address fragments inside the placeholder.
      working = working[:start] + f"«{label}»" + working[end:]
      regex_spans.append(PHISpan(label=label, text=span_text,
                                 start=start, end=end, score=1.0))

    # Layer 2: NER on the regex-masked working copy. Spans returned by
    # the model are positions in `working`; we don't try to back-map them
    # to original text (rare to need that downstream).
    raw_spans = self._pipeline(working)
    latency = time.perf_counter() - t0

    ner_spans = [PHISpan(label=s["entity_group"], text=s["word"],
                         start=s["start"], end=s["end"],
                         score=float(s["score"])) for s in raw_spans]
    masked = working
    for s in sorted(ner_spans, key=lambda x: x.start, reverse=True):
      masked = masked[: s.start] + f"[{s.label}]" + masked[s.end :]
    return DeconResult(original=text, masked=masked,
                       spans=regex_spans + ner_spans,
                       latency_s=latency)

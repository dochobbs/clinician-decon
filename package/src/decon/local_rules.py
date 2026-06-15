"""Local deterministic decontextualization for the desktop prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Iterable

from .destinations import build_handoff, render_prompt


@dataclass(frozen=True)
class Span:
  category: str
  start: int
  end: int


@dataclass(frozen=True)
class LocalDeconResult:
  original_length: int
  destination: str
  safe_context: str
  safe_query: str
  destination_prompt: str
  removed_categories: dict[str, int]
  risk_level: str
  risk_reasons: list[str]
  copy_allowed: bool
  open_url: str | None
  action_label: str


AGE_UNITS = r"yo|y/o|yrs?|years? old|months? old|months?|mo"
EXPLICIT_AGE_UNITS = r"yo|y/o|yrs?|years? old|months? old|mo"
LAB_TERMS = r"A1c|HbA1c|INR|TSH|LDH|WBC|platelets?|ferritin|lipase|amylase"
MONTH_TERMS = (
  r"January|February|March|April|May|June|July|August|September|October|November|"
  r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
RELATION_TERMS = (
  r"Mom|Mama|Mami|Mother|Dad|Papa|Father|Grandma|Grandpa|Aunt|Auntie|Uncle|"
  r"Tia|Tio|Abuela|Abuelo|Wife|Husband|Spouse|Partner|Sister|Brother|Daughter|"
  r"Son|Guardian|Caregiver"
)
STREET_TYPES = (
  r"St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Ln|Lane|Way|Ct|Court|"
  r"Pkwy|Parkway"
)
NAME_TOKEN = (
  r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]+|[A-ZÀ-ÖØ-Þ])"
  r"(?:[-'][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]+)?"
)
NAME_PARTICLES = r"van|von|der|den|de|del|da|la|le|di|du|dos|das"
FULL_NAME = rf"{NAME_TOKEN}(?:\s+(?:(?:{NAME_PARTICLES})\s+)*{NAME_TOKEN}){{1,3}}"
NAME_CUES = (
  r"DOB|MRN|on|has|with|presents|asks?|needs|due|from|is|came|called|wants|"
  r"says|lives|peri-menopausal"
)

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("prompt_injection", re.compile(
    r"\b(?:ignore|disregard|override)\s+(?:your\s+|all\s+)?(?:previous|prior|above)\s+"
    r"instructions\b[^.?!]*(?:[.?!]|$)",
    re.IGNORECASE,
  )),
  ("contextual_identifier", re.compile(r"\bonly case\b", re.IGNORECASE)),
  ("address", re.compile(
    rf"\b\d{{1,6}}\s+(?:[A-Za-z0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?",
    re.IGNORECASE,
  )),
  ("location", re.compile(
    rf"\b(?i:(?:lives?|resides|located)\s+(?:at|in))\s+"
    rf"\d{{1,6}}\s+(?:[A-Za-z0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?,\s*"
    rf"({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})\b",
  )),
  ("location", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2},\s*[A-Z]{2}\b")),
  ("location", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b")),
  ("location", re.compile(
    rf"\b(?i:(?:from|near|in|at))\s+({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})"
    r"(?=\s*(?:[-,.;)]|$))",
  )),
  ("zip", re.compile(r"\b(?:ZIP|zip code)\s*[:#]?\s*(\d{5}(?:-\d{4})?)\b", re.IGNORECASE)),
  ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("phone", re.compile(r"(?:\+1[\s-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  ("ssn", re.compile(
    r"\b(?:SSN|Social[\s-]?Security[\s-]?(?:Number|#)?)\s*[:#]?\s*"
    r"(\d{3}[-\s]?\d{2}[-\s]?\d{4}|\d{9})\b",
    re.IGNORECASE,
  )),
  ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  ("mrn", re.compile(r"\b(?:MRN|MR#|medical record(?: number)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,})\b", re.IGNORECASE)),
  ("mrn", re.compile(r"\b[A-Z]{1,5}-\d{3,5}-\d{3,6}\b")),
  ("url", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
  ("practice", re.compile(
    r"\b(?:Lakes\s+Pediatrics|Children['’]s(?:\s+Hospital)?|Mayo\s+Clinic|Cleveland\s+Clinic|"
    r"[A-Z][A-Za-z'’.-]+\s+(?:Pediatrics|Clinic|Hospital|Family Medicine|Medical Group|"
    r"Health|Urgent Care))\b",
    re.IGNORECASE,
  )),
  ("insurance", re.compile(
    r"\b(?:Blue\s+Cross|BCBS|Aetna|Cigna|UnitedHealth(?:care)?|Kaiser|Humana|"
    r"Anthem|Medicaid|Medicare|Tricare)\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b")),
  ("date", re.compile(
    r"\b(?:today|yesterday|last\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(rf"\b(?:{MONTH_TERMS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.IGNORECASE)),
  ("date", re.compile(r"\blast\s+week\b", re.IGNORECASE)),
  ("body_measurement", re.compile(r"\bBMI\s*\d{1,2}(?:\.\d+)?\b", re.IGNORECASE)),
  ("body_measurement", re.compile(r"\b\d{2,3}\s*(?:lbs?|kg|pounds?)\b", re.IGNORECASE)),
  ("body_measurement", re.compile(r"\b\d{1,2}'\s*\d{1,2}\"|\b\d{1,2}\s*ft\s*\d{1,2}\s*in\b", re.IGNORECASE)),
  ("clinical_value", re.compile(
    rf"\b(?:{LAB_TERMS})\s*(?:came\s+back\s+at|was|were|is|of|at|[:=])?\s*"
    r"\d[\d.,]*(?:k)?\b",
    re.IGNORECASE,
  )),
  ("age", re.compile(r"\b\d{1,3}\s*(?:M|F)\b", re.IGNORECASE)),
  ("age", re.compile(rf"\b(?:he'?s|she'?s|patient is|pt is)\s+(\d{{1,3}}\s+months?)\b", re.IGNORECASE)),
  ("age", re.compile(rf"\b\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b", re.IGNORECASE)),
  ("relation", re.compile(
    r"\b(?:the\s+)?(?:twins'?|siblings'?)\s+(?:older|younger|baby|little)?\s*"
    r"(?:brother|sister|sibling|kid|child)\b",
    re.IGNORECASE,
  )),
  ("nickname", re.compile(r"\b(?i:(?:Lil|Little|Big|Lil'))\s+(?:[A-Z](?:\.|\b)|[A-Z][a-z]{1,3})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:La\s+mam[aá]|El\s+pap[aá]|Mi\s+hij[oa]|Su\s+hij[oa]|El\s+paciente|"
    rf"La\s+paciente)\s+(?:de\s+)?){NAME_TOKEN}\b",
  )),
  ("name", re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+({NAME_TOKEN})(?='s\b|\b)")),
  ("name", re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+({FULL_NAME})\b")),
  ("name", re.compile(rf"\b(?i:(?:{RELATION_TERMS}))\s+({NAME_TOKEN})\b")),
  ("name", re.compile(rf"\b(?i:(?:{RELATION_TERMS}))\s+\(({NAME_TOKEN})\)(?=\W|$)")),
  ("name", re.compile(rf"\b(?i:little)\s+({NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:SUBJECTIVE|HPI|CC|HISTORY|ASSESSMENT))\s*:\s*({FULL_NAME})"
    r"(?=\s*(?:,|\d))",
  )),
  ("name", re.compile(
    rf"\b(?i:(?:Patient|Pt))\s+({NAME_TOKEN})"
    r"(?=\s+(?:has|presents|needs|asks|is|was|reports|states)\b)",
  )),
  ("name", re.compile(
    rf"^({NAME_TOKEN})(?=\s+(?:has|presents|needs|asks|is|was|reports|states)\b)"
  )),
  ("name", re.compile(rf"\b(?:calls?\s+(?:him|her|them)|known\s+as|nicknamed)\s+({NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:Pt|Patient|Family of|chart for|for patient|for pt))\s+({FULL_NAME})"
    rf"(?=\s*(?:,|\(|\b(?i:(?:{NAME_CUES}))\b|\d{{1,3}}\s*(?:M|F)\b|\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b))",
  )),
  ("name", re.compile(
    rf"\b({NAME_TOKEN})\s+\(\s*\d{{1,3}}\s*(?:M|F|{EXPLICIT_AGE_UNITS})\s*\)",
  )),
  ("name", re.compile(
    rf"^({FULL_NAME})(?=\s*(?:,|\(|\b(?i:(?:{NAME_CUES}))\b|\d{{1,3}}\s*(?:M|F)\b|"
    rf"\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b))"
  )),
  ("name", re.compile(
    rf"\b(?!(?:{RELATION_TERMS})\s)"
    rf"({FULL_NAME})\s+"
    rf"(?:DOB|MRN|came|asks?|called|has|with|\d{{1,3}}\s*(?:{AGE_UNITS}))\b"
  )),
)

RESIDUAL_HIGH_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible MRN or record identifier remains", re.compile(r"\b(?:MRN|MR#|record)\s+[A-Z0-9-]{6,}\b", re.IGNORECASE)),
  ("possible ZIP code remains", re.compile(r"\b(?:ZIP|zip code)\s*[:#]?\s*\d{5}(?:-\d{4})?\b", re.IGNORECASE)),
  ("possible email remains", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("possible phone remains", re.compile(r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  ("possible SSN remains", re.compile(r"\b(?:SSN|Social Security)\s*[:#]?\s*(?:\d{3}-\d{2}-\d{4}|\d{9})\b", re.IGNORECASE)),
  ("possible SSN remains", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  ("possible patient URL remains", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
  ("possible prompt injection remains", re.compile(r"\b(?:ignore|disregard|override)\s+(?:previous|prior|above)\s+instructions\b", re.IGNORECASE)),
  ("possible city/state location remains", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2},\s*[A-Z]{2}\b")),
  ("possible practice or facility remains", re.compile(r"\b[A-Z][A-Za-z'’.-]+\s+(?:Pediatrics|Clinic|Hospital|Medical Group|Health|Urgent Care)\b")),
)

RESIDUAL_MEDIUM_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible exact date remains", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
  ("possible direct name remains", re.compile(r"\b(?:Mr|Mrs|Ms|Miss)\.?\s+[A-Z][a-z]{2,}\b")),
  ("possible patient name remains", re.compile(
    rf"\b(?:Pt|Patient|Family of|chart for|for patient|for pt)\s+{FULL_NAME}\b",
    re.IGNORECASE,
  )),
)

QUERY_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
  re.compile(r"\b(?:DOB|MRN|MR#)\b", re.IGNORECASE),
  re.compile(r"\b(?:came in|called from|asking|asks?|today|at this age)\b", re.IGNORECASE),
  re.compile(r"\b(?:he|she|his|her|him|mom|mother|dad|father)\b", re.IGNORECASE),
)

RELATION_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
  (re.compile(r"\b(?:Mom|Mother|Dad|Father)\s+\[NAME\]", re.IGNORECASE), "parent"),
  (re.compile(r"\b(?:Mom|Mother|Dad|Father)\s+\(\[NAME\]\)", re.IGNORECASE), "parent"),
  (re.compile(r"\blittle\s+\[NAME\]", re.IGNORECASE), "child"),
  (re.compile(r"\b(?:Wife|Husband|Spouse|Partner)\s+\[NAME\]", re.IGNORECASE), "spouse"),
  (re.compile(r"\b(?:Sister|Brother)\s+\[NAME\]", re.IGNORECASE), "sibling"),
  (re.compile(r"\b(?:Daughter|Son)\s+\[NAME\]", re.IGNORECASE), "child"),
  (re.compile(r"\b(?:Grandma|Grandpa)\s+\[NAME\]", re.IGNORECASE), "grandparent"),
  (re.compile(r"\b(?:Guardian|Caregiver)\s+\[NAME\]", re.IGNORECASE), "caregiver"),
  (re.compile(r"\b(?:Aunt|Uncle)\s+\[NAME\]", re.IGNORECASE), "relative"),
)

DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%Y-%m-%d")


def _collect_spans(text: str) -> list[Span]:
  spans: list[Span] = []
  for category, pattern in PATTERNS:
    for match in pattern.finditer(text):
      if match.lastindex:
        start, end = match.span(match.lastindex)
      else:
        start, end = match.span(0)
      if start != end:
        spans.append(Span(category=category, start=start, end=end))
  return _select_non_overlapping(spans)


def _select_non_overlapping(spans: Iterable[Span]) -> list[Span]:
  selected: list[Span] = []
  last_end = -1
  for span in sorted(spans, key=lambda item: (item.start, -(item.end - item.start))):
    if span.start >= last_end:
      selected.append(span)
      last_end = span.end
  return selected


def _apply_spans(text: str, spans: list[Span], reference_date: date) -> tuple[str, dict[str, int]]:
  safe = text
  counts: dict[str, int] = {}
  for span in sorted(spans, key=lambda item: item.start, reverse=True):
    counts[span.category] = counts.get(span.category, 0) + 1
    replacement = _replacement_for_span(text, span, reference_date)
    safe = safe[:span.start] + replacement + safe[span.end:]
  safe = _normalize_safe_context(safe)
  safe = re.sub(r"\s+", " ", safe).strip()
  return safe, dict(sorted(counts.items()))


def _replacement_for_span(text: str, span: Span, reference_date: date) -> str:
  raw = text[span.start:span.end]
  if span.category == "prompt_injection":
    return ""
  if span.category == "contextual_identifier":
    return "Rare case"
  if span.category == "relation":
    return "sibling contact"
  if span.category == "age":
    return _normalize_age(raw)
  if span.category == "body_measurement":
    return _generalize_body_measurement(raw)
  if span.category == "clinical_value":
    return _generalize_clinical_value(raw)
  if span.category == "date":
    derived_age = _derive_age_for_date(text, span, reference_date)
    if derived_age:
      return derived_age
    return _generalize_date(raw)
  return f"[{span.category.upper()}]"


def _normalize_safe_context(text: str) -> str:
  safe = text
  safe = re.sub(
    r"\bDOB\s+(?=(?:newborn|\d{1,2}-month-old|\d{1,3}-year-old|90 or older)\b)",
    "",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(r"\b(?:MRN|MR#)\s+\[MRN\]", "[MRN]", safe, flags=re.IGNORECASE)
  safe = re.sub(r"\bSSN\s+\[SSN\]", "[SSN]", safe, flags=re.IGNORECASE)
  for pattern, replacement in RELATION_REPLACEMENTS:
    safe = pattern.sub(replacement, safe)
  safe = re.sub(r"\s+([,.;:])", r"\1", safe)
  return safe


def _normalize_age(raw: str) -> str:
  compact_match = re.search(
    r"\b(?P<amount>\d{1,3})\s*(?P<sex>M|F)\b",
    raw,
    flags=re.IGNORECASE,
  )
  if compact_match:
    amount = int(compact_match.group("amount"))
    sex = "male" if compact_match.group("sex").lower() == "m" else "female"
    if amount >= 90:
      return f"90 or older {sex}"
    return f"{amount}-year-old {sex}"
  match = re.search(
    rf"\b(?P<amount>\d{{1,3}})\s*(?P<unit>{AGE_UNITS})\b",
    raw,
    flags=re.IGNORECASE,
  )
  if not match:
    return "[AGE]"
  amount = int(match.group("amount"))
  unit = match.group("unit").lower()
  if unit in ("mo", "month", "months", "month old", "months old"):
    return f"{amount}-month-old"
  if amount >= 90:
    return "90 or older"
  return f"{amount}-year-old"


def _parse_date(raw: str) -> date | None:
  for date_format in DATE_FORMATS:
    try:
      return datetime.strptime(raw, date_format).date()
    except ValueError:
      continue
  return None


def _age_from_dob(dob: date, reference_date: date) -> str | None:
  if dob > reference_date:
    return None
  years = reference_date.year - dob.year
  if (reference_date.month, reference_date.day) < (dob.month, dob.day):
    years -= 1
  if years >= 90:
    return "90 or older"
  if years >= 2:
    return f"{years}-year-old"
  months = (reference_date.year - dob.year) * 12 + reference_date.month - dob.month
  if reference_date.day < dob.day:
    months -= 1
  if months <= 0:
    return "newborn"
  return f"{months}-month-old"


def _derive_age_for_date(text: str, span: Span, reference_date: date) -> str | None:
  context = text[max(0, span.start - 24):span.start].lower()
  if not re.search(r"\b(?:dob|date of birth|born)\b", context):
    return None
  parsed = _parse_date(text[span.start:span.end])
  if parsed is None:
    return None
  return _age_from_dob(parsed, reference_date)


def _extract_safe_age(source: str, reference_date: date) -> str | None:
  compact_age = re.search(r"\b\d{1,3}\s*(?:M|F)\b", source, flags=re.IGNORECASE)
  if compact_age:
    return _normalize_age(compact_age.group(0))
  contextual_month_age = re.search(
    r"\b(?:he'?s|she'?s|patient is|pt is)\s+(\d{1,3}\s+months?)\b",
    source,
    flags=re.IGNORECASE,
  )
  if contextual_month_age:
    return _normalize_age(contextual_month_age.group(1))
  explicit_age = re.search(
    rf"\b\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b",
    source,
    flags=re.IGNORECASE,
  )
  if explicit_age:
    return _normalize_age(explicit_age.group(0))
  dob_match = re.search(
    r"\b(?:DOB|date of birth|born)\s*[:#-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b",
    source,
    flags=re.IGNORECASE,
  )
  if dob_match:
    parsed = _parse_date(dob_match.group(1))
    if parsed:
      return _age_from_dob(parsed, reference_date)
  return None


def _is_pediatric_age(age: str | None) -> bool:
  if age is None:
    return False
  if age == "newborn" or "month-old" in age:
    return True
  match = re.match(r"(\d{1,3})-year-old", age)
  return bool(match and int(match.group(1)) < 18)


def _generalize_date(raw: str) -> str:
  lowered = raw.lower()
  if lowered == "today":
    return "same-day"
  if lowered == "yesterday":
    return "1 day prior"
  if lowered.startswith("last "):
    return "recent"
  return "[DATE]"


def _generalize_clinical_value(raw: str) -> str:
  match = re.search(
    rf"\b(?P<label>{LAB_TERMS})\s*(?:came\s+back\s+at|was|were|is|of|at|[:=])?\s*"
    r"(?P<value>\d[\d.,]*(?:k)?)\b",
    raw,
    re.IGNORECASE,
  )
  if not match:
    return "[CLINICAL_VALUE]"
  label = match.group("label")
  normalized_label = "A1c" if label.lower() in ("a1c", "hba1c") else label.upper()
  value_text = match.group("value").replace(",", "").lower()
  multiplier = 1000 if value_text.endswith("k") else 1
  value_text = value_text.removesuffix("k")
  try:
    value = float(value_text) * multiplier
  except ValueError:
    return f"{normalized_label} value"
  if normalized_label == "A1c":
    if value >= 6.5:
      return "elevated A1c"
    return "A1c value"
  if normalized_label == "TSH":
    if value > 4.5:
      return "elevated TSH"
    if value < 0.4:
      return "low TSH"
    return "TSH value"
  return f"{normalized_label} value"


def _generalize_body_measurement(raw: str) -> str:
  bmi_match = re.search(r"\bBMI\s*(?P<value>\d{1,2}(?:\.\d+)?)\b", raw, re.IGNORECASE)
  if bmi_match:
    value = float(bmi_match.group("value"))
    if value >= 30:
      return "obesity-range BMI"
    if value >= 25:
      return "overweight-range BMI"
    return "BMI value"
  if re.search(r"\b\d{1,2}'\s*\d{1,2}\"|\b\d{1,2}\s*ft\s*\d{1,2}\s*in\b", raw, re.IGNORECASE):
    return "height value"
  if re.search(r"\b\d{2,3}\s*(?:lbs?|kg|pounds?)\b", raw, re.IGNORECASE):
    return "weight value"
  return "[BODY_MEASUREMENT]"


def _safe_query_from_context(safe_context: str) -> str:
  query = re.sub(r"\[[A-Z_]+\]", " ", safe_context)
  for pattern in QUERY_NOISE_PATTERNS:
    query = pattern.sub(" ", query)
  query = re.sub(r"\s+", " ", query).strip(" ,.;:-")
  return query or "de-identified clinical question"


def _safe_query_from_text(source: str, safe_context: str, reference_date: date) -> str:
  lower_source = source.lower()
  safe_age = _extract_safe_age(source, reference_date)
  age_prefix = f"{safe_age} " if safe_age else ""
  pediatric_label = "pediatric " if safe_age is None or _is_pediatric_age(safe_age) else ""
  if re.search(r"\b(?:hpv|human papillomavirus)\b", lower_source):
    return f"{age_prefix}{pediatric_label}HPV vaccine schedule current guidelines".strip()
  if re.search(r"\b(?:vaccine|vaccines|vaccination|immunization|shots)\b", lower_source):
    return f"{age_prefix}{pediatric_label}immunization schedule vaccines current guidelines".strip()
  return _safe_query_from_context(safe_context)


def _risk(safe_context: str) -> tuple[str, list[str]]:
  high_reasons = [reason for reason, pattern in RESIDUAL_HIGH_RISK if pattern.search(safe_context)]
  if high_reasons:
    return "high", high_reasons
  medium_reasons = [reason for reason, pattern in RESIDUAL_MEDIUM_RISK if pattern.search(safe_context)]
  if medium_reasons:
    return "medium", medium_reasons
  return "low", []


def decontextualize_text(
  text: str,
  *,
  destination: str,
  reference_date: date | None = None,
) -> LocalDeconResult:
  """Run local rule-based decontextualization and render destination handoff data."""
  source = text.strip()
  ref_date = reference_date or date.today()
  spans = _collect_spans(source)
  safe_context, removed_categories = _apply_spans(source, spans, ref_date)
  safe_query = _safe_query_from_text(source, safe_context, ref_date)
  risk_level, risk_reasons = _risk(safe_context)
  destination_prompt = render_prompt(destination, safe_context=safe_context, safe_query=safe_query)
  handoff = build_handoff(destination, destination_prompt)
  return LocalDeconResult(
    original_length=len(source),
    destination=destination,
    safe_context=safe_context,
    safe_query=safe_query,
    destination_prompt=destination_prompt,
    removed_categories=removed_categories,
    risk_level=risk_level,
    risk_reasons=risk_reasons,
    copy_allowed=risk_level != "high",
    open_url=handoff.open_url,
    action_label=handoff.action_label,
  )

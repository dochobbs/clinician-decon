"""Local deterministic decontextualization for the desktop prototype."""

from __future__ import annotations

from dataclasses import dataclass
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


PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("phone", re.compile(r"(?:\+1[\s-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  ("mrn", re.compile(r"\b(?:MRN|MR#|medical record(?: number)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,})\b", re.IGNORECASE)),
  ("mrn", re.compile(r"\b[A-Z]{1,5}-\d{3,5}-\d{3,6}\b")),
  ("url", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
  ("date", re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b")),
  ("date", re.compile(r"\b(?:today|yesterday|last\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", re.IGNORECASE)),
  ("clinical_value", re.compile(r"\b(?:A1c|HbA1c|INR|TSH|LDH|WBC|platelets?|ferritin|lipase|amylase)\s*[:=]?\s*\d[\d.,]*\b", re.IGNORECASE)),
  ("age", re.compile(r"\b\d{1,3}\s*(?:yo|y/o|year old|years old|months old|mo)\b", re.IGNORECASE)),
  ("name", re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b")),
  ("name", re.compile(r"\b(?:Mom|Mother|Dad|Father|Grandma|Grandpa|Aunt|Uncle)\s+([A-Z][a-z]{2,})\b")),
  ("name", re.compile(r"\b(?:Mom|Mother|Dad|Father|Grandma|Grandpa|Aunt|Uncle)\s+\(([A-Z][a-z]{2,})\)\b")),
  ("name", re.compile(r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\s+(?:DOB|MRN|came|asks?|called|has|with)\b")),
)

RESIDUAL_HIGH_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible MRN or record identifier remains", re.compile(r"\b(?:MRN|MR#|record)\s+[A-Z0-9-]{6,}\b", re.IGNORECASE)),
  ("possible email remains", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("possible phone remains", re.compile(r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  ("possible SSN remains", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  ("possible patient URL remains", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
)

RESIDUAL_MEDIUM_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible exact date remains", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
  ("possible direct name remains", re.compile(r"\b(?:Mr|Mrs|Ms|Miss)\.?\s+[A-Z][a-z]{2,}\b")),
)

QUERY_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
  re.compile(r"\b(?:DOB|MRN|MR#)\b", re.IGNORECASE),
  re.compile(r"\b(?:came in|called from|asking|asks?|today|at this age)\b", re.IGNORECASE),
  re.compile(r"\b(?:he|she|his|her|him|mom|mother|dad|father)\b", re.IGNORECASE),
)


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


def _apply_spans(text: str, spans: list[Span]) -> tuple[str, dict[str, int]]:
  safe = text
  counts: dict[str, int] = {}
  for span in sorted(spans, key=lambda item: item.start, reverse=True):
    counts[span.category] = counts.get(span.category, 0) + 1
    safe = safe[:span.start] + f"[{span.category.upper()}]" + safe[span.end:]
  safe = re.sub(r"\s+", " ", safe).strip()
  return safe, dict(sorted(counts.items()))


def _safe_query_from_context(safe_context: str) -> str:
  query = re.sub(r"\[[A-Z_]+\]", " ", safe_context)
  for pattern in QUERY_NOISE_PATTERNS:
    query = pattern.sub(" ", query)
  query = re.sub(r"\s+", " ", query).strip(" ,.;:-")
  return query or "de-identified clinical question"


def _safe_query_from_text(source: str, safe_context: str) -> str:
  lower_source = source.lower()
  if re.search(r"\b(?:hpv|human papillomavirus)\b", lower_source):
    return "HPV vaccine schedule current guidelines"
  if re.search(r"\b(?:vaccine|vaccines|vaccination|immunization|shots)\b", lower_source):
    return "pediatric immunization schedule vaccines current guidelines"
  return _safe_query_from_context(safe_context)


def _risk(safe_context: str) -> tuple[str, list[str]]:
  high_reasons = [reason for reason, pattern in RESIDUAL_HIGH_RISK if pattern.search(safe_context)]
  if high_reasons:
    return "high", high_reasons
  medium_reasons = [reason for reason, pattern in RESIDUAL_MEDIUM_RISK if pattern.search(safe_context)]
  if medium_reasons:
    return "medium", medium_reasons
  return "low", []


def decontextualize_text(text: str, *, destination: str) -> LocalDeconResult:
  """Run local rule-based decontextualization and render destination handoff data."""
  source = text.strip()
  spans = _collect_spans(source)
  safe_context, removed_categories = _apply_spans(source, spans)
  safe_query = _safe_query_from_text(source, safe_context)
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

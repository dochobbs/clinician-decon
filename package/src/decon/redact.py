"""Deterministic PHI scrubbing before model transformation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List

from .tasks import TaskPolicy
from .validate import generate_date_formats

STOP_PHRASES = (
  "ignore your previous instructions",
  "hipaa filter has been disabled",
  "include all patient details",
  "search for:",
)


@dataclass
class ScrubResult:
  """Result of deterministic scrubbing."""

  scrubbed_text: str
  removed_markers: List[str]


def _replace_all(text: str, patterns: List[str], replacement: str, removed_markers: List[str], marker: str) -> str:
  for pattern in patterns:
    if not pattern:
      continue
    new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    if new_text != text:
      removed_markers.append(marker)
      text = new_text
  return text


def scrub_text(text: str, patient_context: Dict[str, Any], policy: TaskPolicy) -> ScrubResult:
  """Remove direct identifiers and obvious risky strings before LLM processing."""
  scrubbed = text
  removed: List[str] = []

  for phrase in STOP_PHRASES:
    if phrase in scrubbed.lower():
      scrubbed = re.sub(re.escape(phrase), "", scrubbed, flags=re.IGNORECASE)
      removed.append("prompt_injection_phrase")

  name = str(patient_context.get("name", "")).strip()
  if name:
    name_parts = [part for part in re.split(r"[^A-Za-z]+", name) if len(part) > 1]
    for part in sorted(name_parts, key=len, reverse=True):
      scrubbed = re.sub(rf"\b{re.escape(part)}\b", "[NAME]", scrubbed, flags=re.IGNORECASE)
    removed.append("name")

  mrn = str(patient_context.get("mrn", "")).strip()
  if mrn:
    scrubbed = scrubbed.replace(mrn, "[MRN]")
    removed.append("mrn")

  dob = str(patient_context.get("dob", "")).strip()
  if dob:
    for variant in generate_date_formats(dob):
      scrubbed = re.sub(re.escape(variant), "[DOB]", scrubbed, flags=re.IGNORECASE)
    removed.append("dob")

  email = str(patient_context.get("email", "")).strip()
  if email:
    scrubbed = scrubbed.replace(email, "[EMAIL]")
    removed.append("email")

  scrubbed = _replace_all(scrubbed, [r"\b\d{3}-\d{2}-\d{4}\b"], "[SSN]", removed, "ssn")
  scrubbed = _replace_all(scrubbed, [r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"], "[PHONE]", removed, "phone")
  scrubbed = _replace_all(scrubbed, [r"https?://\S+", r"\bmychart\.\S+"], "[URL]", removed, "url")
  scrubbed = _replace_all(scrubbed, [r"\b[A-Z]{1,4}-\d{4}-\d{4,6}\b"], "[MRN]", removed, "mrn_like")

  if not policy.allow_relative_dates:
    scrubbed = _replace_all(
      scrubbed,
      [
        r"\btoday\b",
        r"\byesterday\b",
        r"\blast (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{2,4})?\b",
      ],
      "[DATE]",
      removed,
      "date",
    )

  if not policy.allow_exact_age:
    scrubbed = _replace_all(
      scrubbed,
      [
        r"\b\d{1,3}\s*(?:yo|y/o|year old|years old)\b",
        r"\b\d{1,2}\s*(?:mo|months old)\b",
        r"\b\d{1,3}[MF]\b",
      ],
      "[AGE]",
      removed,
      "age",
    )

  if not policy.allow_specific_labs:
    scrubbed = _replace_all(
      scrubbed,
      [
        r"\b(?:A1c|HbA1c|INR|TSH|LDH|WBC|platelets?|ferritin|lipase|amylase)\s*[:=]?\s*\d[\d.,]*\b",
        r"\b\d[\d.,]*\s*(?:lbs|lb|kg|mg/dL|ng/mL|U/L|K)\b",
      ],
      "[CLINICAL_VALUE]",
      removed,
      "lab_or_measurement",
    )

  scrubbed = re.sub(r"\s+", " ", scrubbed).strip()
  return ScrubResult(scrubbed_text=scrubbed, removed_markers=sorted(set(removed)))

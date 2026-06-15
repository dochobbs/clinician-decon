"""Regex-based PHI validation."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Optional, Set

CLINICAL_TERMS = {
  "and",
  "adult",
  "adolescent",
  "baby",
  "boy",
  "child",
  "elderly",
  "female",
  "girl",
  "hunter",
  "infant",
  "male",
  "newborn",
  "pediatric",
  "pediatrics",
  "teen",
  "toddler",
  "metformin",
  "woman",
  "women",
  "man",
  "men",
}

NAME_STOPWORDS = {
  "and",
  "the",
  "his",
  "her",
  "their",
}

EPONYM_SUFFIXES = (
  "disease",
  "syndrome",
  "phenomenon",
  "sign",
  "criteria",
  "sequence",
  "triad",
  "variant",
)

DATE_FORMATS = (
  "%Y-%m-%d",
  "%m/%d/%Y",
  "%m/%d/%y",
)


class PHILeakError(ValueError):
  """Raised when PHI-like content is found in a search query."""


def generate_date_formats(dob: str) -> Set[str]:
  """Generate common DOB string variants for exact matching."""
  dob = dob.strip()
  matches = {dob}
  for fmt in DATE_FORMATS:
    try:
      dt = datetime.strptime(dob, fmt)
      matches.update({
        dt.strftime("%Y-%m-%d"),
        dt.strftime("%m/%d/%Y"),
        dt.strftime("%-m/%-d/%Y"),
        dt.strftime("%m/%d/%y"),
        dt.strftime("%-m/%-d/%y"),
        dt.strftime("%B %-d %Y"),
        dt.strftime("%b %-d %Y"),
      })
      break
    except ValueError:
      continue
  return {item.lower() for item in matches}


def _tokenize_name(name: str) -> list[str]:
  return [
    part for part in re.split(r"[^A-Za-z]+", name)
    if len(part) > 2 and part.lower() not in NAME_STOPWORDS
  ]


def _has_eponym_context(search_query: str, name_part: str, patient_context: Dict) -> bool:
  parts = [part.lower() for part in _tokenize_name(str(patient_context.get("name", "")))]
  if name_part not in parts:
    return False

  for other in parts:
    if other == name_part:
      continue
    for suffix in EPONYM_SUFFIXES:
      patterns = (
        rf"\b{name_part}[-\s]{other}\s+{suffix}\b",
        rf"\b{other}[-\s]{name_part}\s+{suffix}\b",
      )
      if any(re.search(pattern, search_query) for pattern in patterns):
        return True
  return False


def validate_no_phi(
  search_query: str,
  patient_context: Optional[Dict] = None,
) -> bool:
  """Block obvious PHI before sending a query to external search."""
  patient_context = patient_context or {}
  lowered = search_query.lower()

  for part in _tokenize_name(str(patient_context.get("name", ""))):
    name_part = part.lower()
    if name_part in CLINICAL_TERMS:
      continue
    if _has_eponym_context(lowered, name_part, patient_context):
      continue
    if re.search(rf"\b{re.escape(name_part)}\b", lowered):
      raise PHILeakError(f"name component '{part}' found in search query")

  mrn = str(patient_context.get("mrn", "")).strip()
  if mrn and mrn.lower() in lowered:
    raise PHILeakError("mrn found in search query")

  dob = str(patient_context.get("dob", "")).strip()
  if dob:
    for dob_variant in generate_date_formats(dob):
      if dob_variant and dob_variant in lowered:
        raise PHILeakError("dob found in search query")

  if re.search(r"\b\d{3}-\d{2}-\d{4}\b", search_query):
    raise PHILeakError("ssn pattern found in search query")

  if "@" in search_query:
    raise PHILeakError("email found in search query")

  if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", search_query):
    raise PHILeakError("phone number found in search query")

  if re.search(r"\b[A-Z]{1,4}-\d{4}-\d{4,6}\b", search_query):
    raise PHILeakError("mrn-like pattern found in search query")

  if re.search(r"https?://|/patient/", lowered):
    raise PHILeakError("patient url/path found in search query")

  return True

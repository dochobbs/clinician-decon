"""Optional OpenMed PHI-NER span detector.

This module is deliberately optional: importing the app must not require
transformers or a downloaded model. The app calls this only when the local
model setup marker is present or when tests inject a fake detector.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from .local_rules import Span
from .model_setup import DEFAULT_MODEL_ID


class OpenMedUnavailable(RuntimeError):
  """Raised when the local OpenMed model cannot be loaded without network."""


CLINICAL_NAME_SHIELD_TERMS = {
  "addison",
  "down",
  "hunter",
  "kawasaki",
  "marfan",
  "turner",
  "wilson",
}
CLINICAL_NAME_ALWAYS_SHIELD_TERMS = {"kawasaki"}
CLINICAL_NAME_AFTER_CUES = (
  r"disease|syndrome|criteria|sign|triad|classification|test|workup|protocol|"
  r"red flags"
)
CLINICAL_NAME_BEFORE_CUES = (
  "case of",
  "concern for",
  "could this be",
  "diagnosed with",
  "diagnosis of",
  "meet",
  "possible",
  "r/o",
  "rule out",
  "screen for",
  "suspected",
  "workup for",
)


def _category_for_entity(label: str) -> str | None:
  normalized = label.lower().replace("-", "_")
  if any(token in normalized for token in ("name", "person", "patient", "doctor")):
    return "name"
  if "email" in normalized:
    return "email"
  if "phone" in normalized or "fax" in normalized:
    return "phone"
  if "date" in normalized or "dob" in normalized:
    return "date"
  if "address" in normalized or "street" in normalized:
    return "address"
  if "zip" in normalized or "postal" in normalized:
    return "zip"
  if "url" in normalized:
    return "url"
  if "mrn" in normalized or "medical_record" in normalized:
    return "mrn"
  if any(token in normalized for token in ("id", "identifier", "license", "account", "policy")):
    return "identifier"
  if any(token in normalized for token in ("hospital", "clinic", "practice", "organization")):
    return "practice"
  if "location" in normalized or "city" in normalized:
    return "location"
  return None


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
  while start < end and text[start].isspace():
    start += 1
  while end > start and text[end - 1].isspace():
    end -= 1
  return start, end


def _is_word_fragment(text: str, start: int, end: int) -> bool:
  previous_is_word = start > 0 and text[start - 1].isalpha()
  next_is_word = end < len(text) and text[end:end + 1].isalpha()
  return previous_is_word or next_is_word


def _is_clinical_name_shield(text: str, start: int, end: int) -> bool:
  token = text[start:end].strip(" \t\r\n.,;:?!()[]{}\"'")
  normalized = token.lower()
  if normalized not in CLINICAL_NAME_SHIELD_TERMS:
    return False
  if normalized in CLINICAL_NAME_ALWAYS_SHIELD_TERMS:
    return True

  after = text[end:end + 48].lstrip(" \t\r\n-:/")
  if re.match(rf"(?i)(?:{CLINICAL_NAME_AFTER_CUES})\b", after):
    return True

  before = text[max(0, start - 64):start].lower()
  return any(cue in before for cue in CLINICAL_NAME_BEFORE_CUES)


class OpenMedSpanDetector:
  """Load OpenMed locally and convert token-classification entities to spans."""

  def __init__(self, *, model_id: str = DEFAULT_MODEL_ID, model_dir: Path | None = None):
    self.model_id = model_id
    self.model_dir = model_dir
    self._pipeline = None

  def _model_source(self) -> str:
    if self.model_dir and self.model_dir.exists():
      return str(self.model_dir)
    return self.model_id

  def _load(self) -> Any:
    if self._pipeline is not None:
      return self._pipeline
    try:
      from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
    except Exception as exc:  # pragma: no cover - exercised where transformers is absent
      raise OpenMedUnavailable("transformers is not installed") from exc

    model_source = self._model_source()
    try:
      tokenizer = AutoTokenizer.from_pretrained(model_source, local_files_only=True)
      model = AutoModelForTokenClassification.from_pretrained(model_source, local_files_only=True)
      self._pipeline = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device=-1,
      )
    except Exception as exc:  # pragma: no cover - depends on local model files
      raise OpenMedUnavailable(f"could not load local model from {model_source}") from exc
    return self._pipeline

  def __call__(self, text: str) -> list[Span]:
    detector = self._load()
    spans: list[Span] = []
    for entity in detector(text):
      category = _category_for_entity(str(entity.get("entity_group", "")))
      if category is None:
        continue
      start, end = _trim_span(text, int(entity["start"]), int(entity["end"]))
      if category == "name" and _is_word_fragment(text, start, end):
        continue
      if _is_clinical_name_shield(text, start, end):
        continue
      if start < end:
        spans.append(Span(category=category, start=start, end=end))
    return spans


@lru_cache(maxsize=2)
def get_openmed_span_detector(model_id: str = DEFAULT_MODEL_ID, model_dir: str = "") -> OpenMedSpanDetector:
  return OpenMedSpanDetector(model_id=model_id, model_dir=Path(model_dir) if model_dir else None)

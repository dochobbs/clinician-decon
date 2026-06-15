"""Risk scoring for minimized outputs."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List

from .tasks import TaskMode


@dataclass
class RiskAssessment:
  """Simple reidentification risk summary."""

  level: str
  reasons: List[str]
  score: int


def score_reidentification_risk(text: str, patient_context: Dict[str, Any], mode: TaskMode) -> RiskAssessment:
  """Estimate residual reidentification risk in output text."""
  lowered = text.lower()
  score = 0
  reasons: List[str] = []

  for key in ("name", "mrn", "dob", "email"):
    value = str(patient_context.get(key, "")).strip().lower()
    if value and value in lowered:
      score += 5
      reasons.append(f"direct_{key}_match")

  if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
    score += 5
    reasons.append("ssn_pattern")
  if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text):
    score += 4
    reasons.append("phone_pattern")
  if "@" in text:
    score += 4
    reasons.append("email_pattern")
  if re.search(r"https?://|/patient/", lowered):
    score += 4
    reasons.append("url_pattern")

  if mode in (TaskMode.EXTERNAL_WEB_SEARCH, TaskMode.EXTERNAL_GENERAL_LLM, TaskMode.ANALYTICS_EXPORT):
    if re.search(r"\b(today|yesterday|last\s+\w+)\b", lowered):
      score += 1
      reasons.append("relative_date")
    if re.search(r"\b\d{1,3}\s*(?:yo|year old|years old|months old|mo)\b", lowered):
      score += 1
      reasons.append("exact_age")

  if score >= 5:
    level = "high"
  elif score >= 2:
    level = "medium"
  else:
    level = "low"

  return RiskAssessment(level=level, reasons=reasons, score=score)

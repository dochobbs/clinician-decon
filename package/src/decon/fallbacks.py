"""Fallback strategies for unsafe outputs."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .tasks import TaskMode


@dataclass
class FallbackResult:
  """Fallback output details."""

  text: str
  used: bool
  reason: str


def generic_fallback(text: str, mode: TaskMode) -> FallbackResult:
  """Return a broader, safer fallback string."""
  lowered = text.lower()
  if mode == TaskMode.EXTERNAL_WEB_SEARCH:
    generic = "clinical management guideline current guidelines 2025 2026"
    if "vaccine" in lowered or "immunization" in lowered:
      generic = "immunization schedule pediatric current guidelines 2025 2026"
    elif "diabetes" in lowered or "metformin" in lowered:
      generic = "type 2 diabetes management current guidelines 2025 2026"
    elif "hypertension" in lowered or "blood pressure" in lowered:
      generic = "hypertension management current guidelines 2025 2026"
    elif "screen" in lowered or "colonoscopy" in lowered or "mammogram" in lowered:
      generic = "screening recommendations current guidelines 2025 2026"
    return FallbackResult(text=generic, used=True, reason="generic_search_fallback")

  generic = re.sub(r"\s+", " ", text).strip()
  return FallbackResult(text=generic or "clinical topic", used=True, reason="generic_fallback")

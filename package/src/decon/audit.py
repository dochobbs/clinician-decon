"""Structured audit payloads without logging raw PHI-rich text by default."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuditRecord:
  """Minimal structured audit record."""

  mode: str
  provider: str
  model: str
  attempts: int
  validation_passed: bool
  risk_level: str
  risk_reasons: List[str] = field(default_factory=list)
  removed_markers: List[str] = field(default_factory=list)
  fallback_used: bool = False
  fallback_reason: str = ""

  def as_dict(self) -> Dict[str, Any]:
    return {
      "mode": self.mode,
      "provider": self.provider,
      "model": self.model,
      "attempts": self.attempts,
      "validation_passed": self.validation_passed,
      "risk_level": self.risk_level,
      "risk_reasons": self.risk_reasons,
      "removed_markers": self.removed_markers,
      "fallback_used": self.fallback_used,
      "fallback_reason": self.fallback_reason,
    }

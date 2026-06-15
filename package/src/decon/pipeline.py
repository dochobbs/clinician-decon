"""Structured PHI minimization pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .audit import AuditRecord
from .fallbacks import FallbackResult, generic_fallback
from .intent import build_retry_prompt, build_system_prompt
from .redact import ScrubResult, scrub_text
from .risk import RiskAssessment, score_reidentification_risk
from .tasks import TaskMode, get_task_policy
from .validate import PHILeakError, validate_no_phi


@dataclass
class MinimizationResult:
  """Full structured result from a minimization run."""

  safe_text: str
  mode: str
  intent_text: str
  scrubbed_input: str
  raw_output: str
  validation_passed: bool
  risk_level: str
  risk_score: int
  risk_reasons: list[str]
  attempts: int
  fallback_used: bool
  fallback_reason: str
  removed_markers: list[str]
  provider: str
  model: str

  def as_dict(self) -> Dict[str, Any]:
    return {
      "safe_text": self.safe_text,
      "mode": self.mode,
      "intent_text": self.intent_text,
      "scrubbed_input": self.scrubbed_input,
      "raw_output": self.raw_output,
      "validation_passed": self.validation_passed,
      "risk_level": self.risk_level,
      "risk_score": self.risk_score,
      "risk_reasons": self.risk_reasons,
      "attempts": self.attempts,
      "fallback_used": self.fallback_used,
      "fallback_reason": self.fallback_reason,
      "removed_markers": self.removed_markers,
      "provider": self.provider,
      "model": self.model,
    }

  def audit_record(self) -> AuditRecord:
    return AuditRecord(
      mode=self.mode,
      provider=self.provider,
      model=self.model,
      attempts=self.attempts,
      validation_passed=self.validation_passed,
      risk_level=self.risk_level,
      risk_reasons=self.risk_reasons,
      removed_markers=self.removed_markers,
      fallback_used=self.fallback_used,
      fallback_reason=self.fallback_reason,
    )


def minimize_text(
  physician_query: str,
  *,
  patient_context: Optional[Dict[str, Any]],
  mode: TaskMode,
  generator: Any,
  provider_name: str,
  model: str,
  max_attempts: int = 2,
) -> MinimizationResult:
  """Run deterministic scrubbing, model transformation, validation, and fallback."""
  patient_context = patient_context or {}
  policy = get_task_policy(mode)
  scrub: ScrubResult = scrub_text(physician_query, patient_context, policy)
  raw_output = ""
  output = ""
  fallback = FallbackResult(text="", used=False, reason="")

  for attempt in range(1, max_attempts + 1):
    prompt = build_retry_prompt(mode, policy) if attempt > 1 else build_system_prompt(mode, policy)
    raw_output = generator(scrub.scrubbed_text, prompt)
    output = raw_output.strip()
    try:
      if mode in (TaskMode.EXTERNAL_WEB_SEARCH, TaskMode.EXTERNAL_GENERAL_LLM, TaskMode.ANALYTICS_EXPORT):
        validate_no_phi(output, patient_context)
      risk = score_reidentification_risk(output, patient_context, mode)
      if risk.level == "high" and policy.fail_closed:
        raise PHILeakError("high reidentification risk")
      return MinimizationResult(
        safe_text=output,
        mode=mode.value,
        intent_text=output,
        scrubbed_input=scrub.scrubbed_text,
        raw_output=raw_output,
        validation_passed=True,
        risk_level=risk.level,
        risk_score=risk.score,
        risk_reasons=risk.reasons,
        attempts=attempt,
        fallback_used=False,
        fallback_reason="",
        removed_markers=scrub.removed_markers,
        provider=provider_name,
        model=model,
      )
    except PHILeakError as exc:
      if attempt == max_attempts:
        if policy.fail_closed:
          fallback = generic_fallback(scrub.scrubbed_text, mode)
          risk = score_reidentification_risk(fallback.text, patient_context, mode)
          try:
            if mode in (TaskMode.EXTERNAL_WEB_SEARCH, TaskMode.EXTERNAL_GENERAL_LLM, TaskMode.ANALYTICS_EXPORT):
              validate_no_phi(fallback.text, patient_context)
          except PHILeakError:
            fallback = FallbackResult(text="", used=True, reason=str(exc))
            risk = score_reidentification_risk("", patient_context, mode)
          return MinimizationResult(
            safe_text=fallback.text,
            mode=mode.value,
            intent_text=fallback.text,
            scrubbed_input=scrub.scrubbed_text,
            raw_output=raw_output,
            validation_passed=bool(fallback.text),
            risk_level=risk.level,
            risk_score=risk.score,
            risk_reasons=risk.reasons + [str(exc)],
            attempts=attempt,
            fallback_used=True,
            fallback_reason=fallback.reason or str(exc),
            removed_markers=scrub.removed_markers,
            provider=provider_name,
            model=model,
          )
        raise

  raise RuntimeError("minimization attempts exhausted unexpectedly")

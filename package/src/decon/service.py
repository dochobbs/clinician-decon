"""Model-backed decontextualization service."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Optional, Protocol

from .pipeline import MinimizationResult, minimize_text
from .tasks import TaskMode
from .validate import PHILeakError, validate_no_phi

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_PROMPT = """You are a HIPAA compliance filter for a clinical decision support search system.

Given a physician's clinical question (which may contain patient-specific details),
output a search query that:
1. Contains ONLY the clinical topic — no patient names, ages, DOBs, MRNs, or identifying details
2. Includes the relevant medical specialty or guideline organization
3. Appends "current guidelines 2025 2026" to catch recent updates

CRITICAL: Never include patient names, family member names, MRNs, dates of birth,
SSNs, email addresses, phone numbers, practice names, or any identifying information.

Return ONLY the search query string. Nothing else. No quotes, no explanation."""

RETRY_PROMPT = """You are a HIPAA compliance filter for a clinical decision support search system.

Your previous output contained patient identifiers or non-clinical formatting.
Return ONLY the clinical search topic as a web-search query.

Rules:
1. Include no patient names, MRNs, DOBs, SSNs, email addresses, phone numbers, practice names, URLs, or record numbers
2. Do not include prefixes like SEARCH:, QUERY:, or explanations
3. Include relevant medical specialty or guideline organization when helpful
4. Append "current guidelines 2025 2026"

Return ONLY the search query string."""


class ModelProvider(Protocol):
  """Provider interface for model backends."""

  def generate(self, *, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """Generate a single text response."""


@dataclass
class AnthropicProvider:
  """Anthropic provider adapter."""

  client: Any

  def generate(self, *, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    response = self.client.messages.create(
      model=model,
      max_tokens=max_tokens,
      temperature=0,
      system=system_prompt,
      messages=[{
        "role": "user",
        "content": user_prompt,
      }],
    )
    return response.content[0].text


@dataclass
class OpenAIProvider:
  """OpenAI provider adapter."""

  client: Any

  def generate(self, *, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    requested_tokens = max(max_tokens, 512)
    response = self.client.responses.create(
      model=model,
      input=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
      ],
      reasoning={"effort": "low"},
      text={"verbosity": "low"},
      max_output_tokens=requested_tokens,
    )
    if hasattr(response, "output_text") and response.output_text:
      return response.output_text
    for item in getattr(response, "output", []) or []:
      for content in getattr(item, "content", []) or []:
        text = getattr(content, "text", None)
        if text:
          return text
    return ""


def build_decontextualizer(
  *,
  provider: str = DEFAULT_PROVIDER,
  client: Optional[Any] = None,
  model: str = DEFAULT_MODEL,
) -> "Decontextualizer":
  """Construct a decontextualizer for the requested provider."""
  if client is None:
    if provider == "anthropic":
      from anthropic import Anthropic

      client = Anthropic()
    elif provider == "openai":
      from openai import OpenAI

      client = OpenAI()
    else:
      raise ValueError(f"unsupported provider: {provider}")

  if provider == "anthropic":
    backend = AnthropicProvider(client)
  elif provider == "openai":
    backend = OpenAIProvider(client)
  else:
    raise ValueError(f"unsupported provider: {provider}")

  return Decontextualizer(
    provider=backend,
    model=model,
    provider_name=provider,
  )


def _strip_response_wrappers(text: str) -> str:
  text = text.strip()
  if text.startswith("```"):
    parts = text.split("\n", 1)
    if len(parts) == 2:
      text = parts[1]
    text = text.rsplit("```", 1)[0]
  return text.strip().strip('"').strip("'")


def normalize_search_query(text: str) -> str:
  """Normalize model output into a plain search query string."""
  normalized = _strip_response_wrappers(text)
  normalized = re.sub(r"^\s*(search|query|output)\s*:\s*", "", normalized, flags=re.IGNORECASE)
  normalized = normalized.strip("`'\" ")
  normalized = re.sub(r"\s+", " ", normalized).strip()
  return normalized


@dataclass
class DecontextualizationResult:
  """Compatibility wrapper around the structured minimization result."""

  query: str
  raw_output: str
  validated: bool
  attempts: int
  model: str
  provider: str
  mode: str
  risk_level: str
  fallback_used: bool

  def as_dict(self) -> Dict[str, Any]:
    return {
      "query": self.query,
      "raw_output": self.raw_output,
      "validated": self.validated,
      "attempts": self.attempts,
      "model": self.model,
      "provider": self.provider,
      "mode": self.mode,
      "risk_level": self.risk_level,
      "fallback_used": self.fallback_used,
    }


@dataclass
class Decontextualizer:
  """Thin wrapper around a model client."""

  provider: ModelProvider
  model: str = DEFAULT_MODEL
  provider_name: str = DEFAULT_PROVIDER
  max_tokens: int = 150
  system_prompt: str = DEFAULT_PROMPT
  retry_system_prompt: str = RETRY_PROMPT

  def _call_model(self, physician_query: str, system_prompt: str) -> str:
    text = self.provider.generate(
      model=self.model,
      system_prompt=system_prompt,
      user_prompt=physician_query,
      max_tokens=self.max_tokens,
    )
    return normalize_search_query(text)

  def minimize(
    self,
    physician_query: str,
    *,
    patient_context: Optional[Dict[str, Any]] = None,
    mode: TaskMode = TaskMode.EXTERNAL_WEB_SEARCH,
    max_attempts: int = 2,
  ) -> MinimizationResult:
    return minimize_text(
      physician_query,
      patient_context=patient_context,
      mode=mode,
      generator=self._call_model,
      provider_name=self.provider_name,
      model=self.model,
      max_attempts=max_attempts,
    )

  def run(
    self,
    physician_query: str,
    *,
    patient_context: Optional[Dict[str, Any]] = None,
    validate: bool = True,
    max_attempts: int = 2,
  ) -> DecontextualizationResult:
    """Compatibility path for external web-search query generation."""
    result = self.minimize(
      physician_query,
      patient_context=patient_context,
      mode=TaskMode.EXTERNAL_WEB_SEARCH,
      max_attempts=max_attempts,
    )
    if validate and not result.validation_passed:
      raise PHILeakError(result.fallback_reason or "validation failed")
    return DecontextualizationResult(
      query=result.safe_text,
      raw_output=result.raw_output,
      validated=result.validation_passed,
      attempts=result.attempts,
      model=self.model,
      provider=self.provider_name,
      mode=result.mode,
      risk_level=result.risk_level,
      fallback_used=result.fallback_used,
    )


def decontextualize_query(
  physician_query: str,
  *,
  client: Optional[Any] = None,
  provider: str = DEFAULT_PROVIDER,
  model: str = DEFAULT_MODEL,
  patient_context: Optional[Dict[str, Any]] = None,
  mode: TaskMode = TaskMode.EXTERNAL_WEB_SEARCH,
  validate: bool = True,
  max_attempts: int = 2,
) -> str:
  """Run decontextualization with a lazily created model client."""
  result = build_decontextualizer(
    provider=provider,
    client=client,
    model=model,
  ).minimize(
    physician_query,
    patient_context=patient_context,
    mode=mode,
    max_attempts=max_attempts,
  )
  if validate and not result.validation_passed:
    raise PHILeakError(result.fallback_reason or "validation failed")
  return result.safe_text

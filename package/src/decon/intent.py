"""Prompt construction for task-specific clinical intent extraction."""

from __future__ import annotations

from .tasks import TaskMode, TaskPolicy


def build_system_prompt(mode: TaskMode, policy: TaskPolicy) -> str:
  """Construct the task-specific system prompt."""
  base_rules = [
    "You are a PHI minimization and clinical intent extraction system.",
    "Return only the minimized downstream text.",
    "Never include names, MRNs, DOBs, SSNs, email addresses, phone numbers, provider names, practice names, or URLs.",
    "Preserve only the minimum clinical detail needed for the task.",
  ]

  if not policy.allow_exact_age:
    base_rules.append("Generalize exact ages unless clinically essential.")
  if not policy.allow_specific_labs:
    base_rules.append("Avoid exact laboratory values or weights unless strictly required.")
  if not policy.allow_relative_dates:
    base_rules.append("Avoid visit dates and relative time references such as today or yesterday.")

  if mode == TaskMode.EXTERNAL_WEB_SEARCH:
    base_rules.extend([
      "Rewrite the input into a safe external search query.",
      "Include medical specialty or guideline organization only when helpful.",
      "Append 'current guidelines 2025 2026'.",
    ])
  elif mode == TaskMode.EXTERNAL_GENERAL_LLM:
    base_rules.append("Rewrite the input into a safe external LLM prompt without search-optimization terms.")
  elif mode == TaskMode.INTERNAL_RETRIEVAL:
    base_rules.append("Rewrite the input into a concise internal retrieval query, preserving useful clinical specifics.")
  elif mode == TaskMode.INTERNAL_SUMMARIZATION:
    base_rules.append("Rewrite the input into a minimized internal summarization request.")
  elif mode == TaskMode.ANALYTICS_EXPORT:
    base_rules.append("Rewrite the input into a de-identified analytic label string.")

  return "\n".join(base_rules)


def build_retry_prompt(mode: TaskMode, policy: TaskPolicy) -> str:
  """Construct a stricter retry prompt."""
  return (
    build_system_prompt(mode, policy)
    + "\nYour previous output contained identifiers or unsafe details.\n"
      "Return a broader, safer version if needed. Do not preserve unique narrative details."
  )

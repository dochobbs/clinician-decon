"""Task modes and policy definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskMode(str, Enum):
  """Supported downstream minimization targets."""

  EXTERNAL_WEB_SEARCH = "external_web_search"
  EXTERNAL_GENERAL_LLM = "external_general_llm"
  INTERNAL_RETRIEVAL = "internal_retrieval"
  INTERNAL_SUMMARIZATION = "internal_summarization"
  ANALYTICS_EXPORT = "analytics_export"


@dataclass(frozen=True)
class TaskPolicy:
  """Behavioral policy for a task mode."""

  mode: TaskMode
  allow_exact_age: bool
  allow_specific_labs: bool
  allow_relative_dates: bool
  optimize_for_search: bool
  fail_closed: bool


def get_task_policy(mode: TaskMode) -> TaskPolicy:
  """Return the policy associated with a task mode."""
  if mode == TaskMode.EXTERNAL_WEB_SEARCH:
    return TaskPolicy(mode, allow_exact_age=False, allow_specific_labs=False, allow_relative_dates=False, optimize_for_search=True, fail_closed=True)
  if mode == TaskMode.EXTERNAL_GENERAL_LLM:
    return TaskPolicy(mode, allow_exact_age=False, allow_specific_labs=False, allow_relative_dates=False, optimize_for_search=False, fail_closed=True)
  if mode == TaskMode.INTERNAL_RETRIEVAL:
    return TaskPolicy(mode, allow_exact_age=True, allow_specific_labs=True, allow_relative_dates=True, optimize_for_search=False, fail_closed=False)
  if mode == TaskMode.INTERNAL_SUMMARIZATION:
    return TaskPolicy(mode, allow_exact_age=True, allow_specific_labs=True, allow_relative_dates=True, optimize_for_search=False, fail_closed=False)
  if mode == TaskMode.ANALYTICS_EXPORT:
    return TaskPolicy(mode, allow_exact_age=False, allow_specific_labs=False, allow_relative_dates=False, optimize_for_search=False, fail_closed=True)
  raise ValueError(f"unsupported task mode: {mode}")

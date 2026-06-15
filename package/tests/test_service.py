import pytest

from decon.intent import build_retry_prompt
from decon.service import Decontextualizer, normalize_search_query
from decon.tasks import TaskMode, get_task_policy


class _FakeProvider:
  def __init__(self, outputs):
    self.outputs = list(outputs)
    self.calls = []

  def generate(self, **kwargs):
    self.calls.append(kwargs)
    if not self.outputs:
      raise AssertionError("no more fake outputs configured")
    return self.outputs.pop(0)


def test_normalize_search_query_strips_prefix_and_fences():
  text = "```text\nSEARCH: migraine prophylaxis current guidelines 2025 2026\n```"
  assert normalize_search_query(text) == "migraine prophylaxis current guidelines 2025 2026"


def test_run_retries_when_first_output_leaks_phi():
  provider = _FakeProvider([
    "SEARCH: Marcus Johnson vaccine schedule current guidelines 2025 2026",
    "adolescent immunization schedule current guidelines 2025 2026",
  ])
  svc = Decontextualizer(provider=provider)

  result = svc.run(
    "Marcus Johnson needs his vaccines",
    patient_context={"name": "Marcus Johnson"},
  )

  assert result.validated is True
  assert result.attempts == 2
  assert result.query == "adolescent immunization schedule current guidelines 2025 2026"
  assert provider.calls[1]["system_prompt"] == build_retry_prompt(
    TaskMode.EXTERNAL_WEB_SEARCH,
    get_task_policy(TaskMode.EXTERNAL_WEB_SEARCH),
  )


def test_run_falls_back_after_exhausting_attempts():
  provider = _FakeProvider([
    "John Smith diabetes management current guidelines 2025 2026",
    "SEARCH: John Smith type 2 diabetes current guidelines 2025 2026",
  ])
  svc = Decontextualizer(provider=provider)

  result = svc.run(
    "John Smith needs diabetes treatment guidance",
    patient_context={"name": "John Smith"},
  )

  assert result.validated is True
  assert result.fallback_used is True
  assert result.risk_level == "low"
  assert result.query == "type 2 diabetes management current guidelines 2025 2026"

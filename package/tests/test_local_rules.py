from decon.local_rules import decontextualize_text


def test_decontextualize_text_removes_common_identifiers_without_returning_values():
  source = (
    "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. "
    "Mom Jennifer called from 512-555-0147 about vaccine schedule."
  )

  result = decontextualize_text(source, destination="chatgpt")

  assert result.copy_allowed is True
  assert result.risk_level in ("low", "medium")
  assert "Marcus" not in result.safe_context
  assert "Johnson" not in result.safe_context
  assert "Jennifer" not in result.safe_context
  assert "3/15/2013" not in result.safe_context
  assert "LP-2024-08432" not in result.safe_context
  assert "512-555-0147" not in result.safe_context
  assert result.removed_categories["name"] >= 1
  assert result.removed_categories["date"] >= 1
  assert result.removed_categories["mrn"] >= 1
  assert result.removed_categories["phone"] >= 1
  assert "Marcus" not in str(result.removed_categories)
  assert "LP-2024-08432" not in str(result.removed_categories)


def test_decontextualize_text_builds_useful_web_search_query_from_redacted_chart_text():
  source = (
    "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. "
    "Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age."
  )

  result = decontextualize_text(source, destination="web_search")

  assert result.safe_query == "pediatric immunization schedule vaccines current guidelines"
  assert result.destination_prompt == result.safe_query
  assert "DOB" not in result.safe_query
  assert "MRN" not in result.safe_query
  assert "came in" not in result.safe_query
  assert "called from" not in result.safe_query
  assert "Marcus" not in result.safe_query
  assert "Jennifer" not in result.safe_query


def test_decontextualize_text_blocks_copy_when_residual_mrn_remains():
  source = "Please answer for patient record ABCDEFGHIJK with fatigue and bruising."

  result = decontextualize_text(source, destination="gemini")

  assert result.copy_allowed is False
  assert result.risk_level == "high"
  assert any("identifier" in reason.lower() or "record" in reason.lower()
             for reason in result.risk_reasons)


def test_decontextualize_text_renders_destination_prompt():
  source = "Mrs. Eleanor Rigby has A1c 8.2 and asks about metformin dosing."

  result = decontextualize_text(source, destination="claude")

  assert result.destination == "claude"
  assert result.destination_prompt
  assert result.safe_context in result.destination_prompt
  assert "Eleanor" not in result.destination_prompt
  assert "Rigby" not in result.destination_prompt

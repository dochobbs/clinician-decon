from decon.app_server import build_decon_payload, build_setup_status_payload


def test_build_decon_payload_does_not_return_removed_phi_values():
  source = "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 asks about HPV vaccine."

  payload = build_decon_payload({"text": source, "destination": "chatgpt"})

  assert payload["copy_allowed"] is True
  assert "Marcus" not in payload["safe_context"]
  assert "Johnson" not in payload["safe_context"]
  assert "LP-2024-08432" not in payload["destination_prompt"]
  assert "Marcus" not in str(payload["removed_categories"])
  assert payload["handoff"]["open_url"] == "https://chatgpt.com/"
  assert payload["handoff"]["copy_text"] == payload["destination_prompt"]
  assert payload["handoff"]["copy_text"] not in payload["handoff"]["open_url"]


def test_build_decon_payload_copies_clean_web_search_query():
  source = (
    "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. "
    "Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age."
  )

  payload = build_decon_payload({"text": source, "destination": "web_search"})

  assert payload["destination_prompt"] == "13-year-old pediatric immunization schedule vaccines current guidelines"
  assert payload["handoff"]["copy_text"] == payload["destination_prompt"]
  assert payload["handoff"]["open_url"] == "https://www.google.com/"
  assert "DOB" not in payload["destination_prompt"]
  assert "MRN" not in payload["destination_prompt"]


def test_build_decon_payload_rejects_empty_text():
  payload = build_decon_payload({"text": "  ", "destination": "gemini"})

  assert payload["error"] == "empty_text"
  assert payload["copy_allowed"] is False


def test_build_setup_status_payload_is_local(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))

  payload = build_setup_status_payload()

  assert payload["local_rules_ready"] is True
  assert payload["raw_phi_leaves_device"] is False
  assert payload["setup_required"] is True

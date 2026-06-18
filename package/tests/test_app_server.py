from pathlib import Path

from decon.app_server import build_decon_payload, build_setup_status_payload


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_decon_payload_does_not_return_removed_phi_values():
  source = "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 asks about HPV vaccine."

  payload = build_decon_payload({"text": source, "destination": "chatgpt", "engine": "local-rules"})

  assert payload["copy_allowed"] is True
  assert "Marcus" not in payload["safe_context"]
  assert "Johnson" not in payload["safe_context"]
  assert "LP-2024-08432" not in payload["destination_prompt"]
  assert "Marcus" not in str(payload["removed_categories"])
  assert payload["handoff"]["open_url"] == "https://chatgpt.com/"
  assert payload["handoff"]["copy_text"] == payload["destination_prompt"]
  assert payload["handoff"]["copy_text"] not in payload["handoff"]["open_url"]
  assert payload["engine_requested"] == "local-rules"
  assert payload["engine"] == "local-rules"


def test_build_decon_payload_copies_clean_web_search_query():
  source = (
    "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. "
    "Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age."
  )

  payload = build_decon_payload({"text": source, "destination": "web_search", "engine": "local-rules"})

  assert payload["destination_prompt"] == "adolescent immunization schedule vaccines current guidelines"
  assert payload["handoff"]["copy_text"] == payload["destination_prompt"]
  assert payload["handoff"]["open_url"] == "https://www.google.com/"
  assert "DOB" not in payload["destination_prompt"]
  assert "MRN" not in payload["destination_prompt"]


def test_build_decon_payload_rejects_empty_text():
  payload = build_decon_payload({"text": "  ", "destination": "gemini"})

  assert payload["error"] == "empty_text"
  assert payload["copy_allowed"] is False


def test_build_decon_payload_rejects_unsupported_engine():
  payload = build_decon_payload({
    "text": "13-year-old asks about asthma.",
    "destination": "chatgpt",
    "engine": "cloud",
  })

  assert payload["error"] == "unsupported_engine"
  assert payload["copy_allowed"] is False
  assert "Unsupported decon engine" in payload["message"]


def test_build_setup_status_payload_is_local(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))

  payload = build_setup_status_payload()

  assert payload["local_rules_ready"] is True
  assert payload["raw_phi_leaves_device"] is False
  assert payload["setup_required"] is True


def test_build_decon_payload_reports_openmed_fallback_when_model_missing(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))
  source = "Freya DOB 3/15/2013 asks about asthma."

  payload = build_decon_payload({
    "text": source,
    "destination": "chatgpt",
    "engine": "rules+openmed",
  })

  assert payload["engine_requested"] == "rules+openmed"
  assert payload["engine"] == "local-rules"
  assert "OpenMed" in payload["engine_fallback_reason"]
  assert payload["risk_level"] == "high"
  assert payload["copy_allowed"] is False
  assert any("OpenMed" in reason for reason in payload["risk_reasons"])


def test_build_decon_payload_defaults_to_openmed_and_blocks_when_model_missing(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))

  payload = build_decon_payload({
    "text": "Maria Gonzalez-Lopez here for her 2 week checkup.",
    "destination": "chatgpt",
  })

  assert payload["engine_requested"] == "rules+openmed"
  assert payload["engine"] == "local-rules"
  assert "OpenMed" in payload["engine_fallback_reason"]
  assert payload["risk_level"] == "high"
  assert payload["copy_allowed"] is False


def test_static_ui_responses_are_not_cached():
  server_source = (REPO_ROOT / "package" / "src" / "decon" / "app_server.py").read_text(encoding="utf-8")

  assert "def end_headers" in server_source
  assert '"Cache-Control", "no-store, max-age=0"' in server_source


def test_local_shutdown_endpoint_is_available():
  server_source = (REPO_ROOT / "package" / "src" / "decon" / "app_server.py").read_text(encoding="utf-8")

  assert 'parsed.path == "/api/shutdown"' in server_source
  assert "Clinician Decon local app is shutting down" in server_source
  assert "self.server.shutdown" in server_source

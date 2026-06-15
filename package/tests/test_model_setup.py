from pathlib import Path

from decon.model_setup import get_model_status


def test_model_status_uses_local_app_data_dir(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))

  status = get_model_status()

  assert status.decon_home == tmp_path
  assert status.model_dir.parent == tmp_path / "models"
  assert "/" not in status.model_dir.name
  assert status.local_rules_ready is True
  assert status.raw_phi_leaves_device is False


def test_model_status_reports_missing_model_without_network(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))

  status = get_model_status()

  assert status.ner_model_ready is False
  assert status.setup_required is True
  assert "download" in status.next_action.lower()

from pathlib import Path

from decon import model_setup
from decon.model_setup import get_model_status, mark_model_installed


def _write_required_model_files(model_dir: Path):
  model_dir.mkdir(parents=True, exist_ok=True)
  for filename in model_setup.REQUIRED_MODEL_FILES:
    (model_dir / filename).write_text("placeholder", encoding="utf-8")


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


def test_model_status_requires_openmed_runtime_when_metadata_exists(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))
  monkeypatch.setattr(model_setup.importlib.util, "find_spec", lambda name: None)
  _write_required_model_files(model_setup.model_dir_for())

  status = mark_model_installed()

  assert status.ner_model_ready is False
  assert status.setup_required is True
  assert "transformers" in status.next_action.lower()
  assert "transformers" in status.last_error.lower()


def test_mark_model_installed_does_not_create_placeholder_model_files(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))
  monkeypatch.setattr(model_setup.importlib.util, "find_spec", lambda name: object())

  status = mark_model_installed()

  assert status.ner_model_ready is False
  assert status.setup_required is True
  assert "missing model files" in status.last_error.lower()

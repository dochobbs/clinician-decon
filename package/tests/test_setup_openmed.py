from pathlib import Path

from decon import setup_openmed


def test_resolve_target_dir_uses_app_data_when_repo_local_not_requested(tmp_path, monkeypatch):
  monkeypatch.setenv("DECON_HOME", str(tmp_path))

  target_dir = setup_openmed.resolve_target_dir(
    setup_openmed.DEFAULT_MODEL_ID,
    explicit_dir=None,
    repo_local=False,
  )

  assert target_dir == tmp_path / "models" / "OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1"


def test_resolve_target_dir_can_target_repo_local_model_dir():
  target_dir = setup_openmed.resolve_target_dir(
    setup_openmed.DEFAULT_MODEL_ID,
    explicit_dir=None,
    repo_local=True,
  )

  assert target_dir == setup_openmed.LOCAL_MODELS_DIR / "OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1"


def test_write_setup_metadata_records_local_boundary(tmp_path):
  setup_openmed.write_setup_metadata(tmp_path, setup_openmed.DEFAULT_MODEL_ID)

  metadata = (tmp_path / "decon-model.json").read_text(encoding="utf-8")

  assert '"model_id": "OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1"' in metadata
  assert '"raw_phi_leaves_device": false' in metadata
  assert '"install_method": "local-download"' in metadata


def test_missing_required_files_reports_only_absent_files(tmp_path):
  for filename in setup_openmed.REQUIRED_MODEL_FILES[:-1]:
    (tmp_path / filename).write_text("placeholder", encoding="utf-8")

  assert setup_openmed.missing_required_files(tmp_path) == [setup_openmed.REQUIRED_MODEL_FILES[-1]]

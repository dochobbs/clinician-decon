"""Local model setup status for the desktop prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
from typing import Any


DEFAULT_MODEL_ID = "OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1"


@dataclass(frozen=True)
class ModelStatus:
  decon_home: Path
  model_id: str
  model_dir: Path
  local_rules_ready: bool
  ner_model_ready: bool
  setup_required: bool
  raw_phi_leaves_device: bool
  next_action: str
  last_error: str = ""

  def as_dict(self) -> dict[str, Any]:
    data = asdict(self)
    data["decon_home"] = str(self.decon_home)
    data["model_dir"] = str(self.model_dir)
    return data


def get_decon_home() -> Path:
  """Resolve the local app-data directory without creating network side effects."""
  override = os.environ.get("DECON_HOME")
  if override:
    return Path(override).expanduser()
  if platform.system() == "Darwin":
    return Path.home() / "Library" / "Application Support" / "Decon"
  if platform.system() == "Windows":
    base = os.environ.get("APPDATA")
    if base:
      return Path(base) / "Decon"
  return Path.home() / ".decon"


def model_dir_for(model_id: str = DEFAULT_MODEL_ID, decon_home: Path | None = None) -> Path:
  safe_name = model_id.replace("/", "--")
  return (decon_home or get_decon_home()) / "models" / safe_name


def get_model_status(model_id: str = DEFAULT_MODEL_ID) -> ModelStatus:
  """Return local setup status. This function never downloads anything."""
  decon_home = get_decon_home()
  model_dir = model_dir_for(model_id, decon_home)
  metadata_path = model_dir / "decon-model.json"
  ner_ready = metadata_path.exists()
  next_action = (
    "Ready for local regex and NER decontextualization."
    if ner_ready
    else "Download the local privacy model to enable OpenMed NER."
  )
  return ModelStatus(
    decon_home=decon_home,
    model_id=model_id,
    model_dir=model_dir,
    local_rules_ready=True,
    ner_model_ready=ner_ready,
    setup_required=not ner_ready,
    raw_phi_leaves_device=False,
    next_action=next_action,
  )


def mark_model_installed(model_id: str = DEFAULT_MODEL_ID) -> ModelStatus:
  """Create local metadata used by tests/dev setup after a model download completes."""
  status = get_model_status(model_id)
  status.model_dir.mkdir(parents=True, exist_ok=True)
  metadata = {
    "model_id": model_id,
    "raw_phi_leaves_device": False,
    "install_method": "local",
  }
  (status.model_dir / "decon-model.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
  return get_model_status(model_id)

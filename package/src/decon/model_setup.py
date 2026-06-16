"""Local model setup status for the desktop prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import json
import os
from pathlib import Path
import platform
from typing import Any


DEFAULT_MODEL_ID = "OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1"
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODELS_DIR = PACKAGE_ROOT / "local-models"
REQUIRED_MODEL_FILES = (
  "config.json",
  "model.safetensors",
  "tokenizer.json",
  "tokenizer_config.json",
  "special_tokens_map.json",
)


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
  repo_local_model = LOCAL_MODELS_DIR / safe_name
  if decon_home is None and "DECON_HOME" not in os.environ and repo_local_model.exists():
    return repo_local_model
  return (decon_home or get_decon_home()) / "models" / safe_name


def get_model_status(model_id: str = DEFAULT_MODEL_ID) -> ModelStatus:
  """Return local setup status. This function never downloads anything."""
  decon_home = get_decon_home()
  model_dir = model_dir_for(model_id)
  missing_files = [filename for filename in REQUIRED_MODEL_FILES if not (model_dir / filename).is_file()]
  transformers_ready = importlib.util.find_spec("transformers") is not None
  torch_ready = importlib.util.find_spec("torch") is not None
  ner_ready = not missing_files and transformers_ready and torch_ready
  if ner_ready:
    next_action = "Ready for local regex and OpenMed NER decontextualization."
    last_error = ""
  elif missing_files:
    next_action = "Copy or download the local privacy model to enable OpenMed NER."
    last_error = f"Missing model files: {', '.join(missing_files)}"
  elif not transformers_ready:
    next_action = "Install transformers in the app runtime to enable OpenMed NER."
    last_error = "Missing Python dependency: transformers"
  else:
    next_action = "Install torch in the app runtime to enable OpenMed NER."
    last_error = "Missing Python dependency: torch"
  return ModelStatus(
    decon_home=decon_home,
    model_id=model_id,
    model_dir=model_dir,
    local_rules_ready=True,
    ner_model_ready=ner_ready,
    setup_required=not ner_ready,
    raw_phi_leaves_device=False,
    next_action=next_action,
    last_error=last_error,
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

"""Download or verify the local OpenMed PHI-NER model files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .model_setup import (
  DEFAULT_MODEL_ID,
  LOCAL_MODELS_DIR,
  REQUIRED_MODEL_FILES,
  get_decon_home,
  model_dir_for,
)


DOWNLOAD_ALLOW_PATTERNS = (
  ".gitattributes",
  "README.md",
  "added_tokens.json",
  "config.json",
  "model.safetensors",
  "special_tokens_map.json",
  "spm.model",
  "tokenizer.json",
  "tokenizer_config.json",
)


def safe_model_dir_name(model_id: str) -> str:
  return model_id.replace("/", "--")


def resolve_target_dir(
  model_id: str = DEFAULT_MODEL_ID,
  *,
  explicit_dir: str | Path | None = None,
  repo_local: bool = False,
) -> Path:
  if explicit_dir:
    return Path(explicit_dir).expanduser()
  if repo_local:
    return LOCAL_MODELS_DIR / safe_model_dir_name(model_id)
  return model_dir_for(model_id, decon_home=get_decon_home())


def missing_required_files(model_dir: Path) -> list[str]:
  return [filename for filename in REQUIRED_MODEL_FILES if not (model_dir / filename).is_file()]


def write_setup_metadata(model_dir: Path, model_id: str) -> None:
  model_dir.mkdir(parents=True, exist_ok=True)
  metadata = {
    "model_id": model_id,
    "raw_phi_leaves_device": False,
    "install_method": "local-download",
  }
  (model_dir / "decon-model.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def download_model(
  *,
  model_id: str = DEFAULT_MODEL_ID,
  target_dir: Path,
  local_files_only: bool = False,
) -> Path:
  try:
    from huggingface_hub import snapshot_download
  except ImportError as exc:  # pragma: no cover - depends on optional runtime
    raise RuntimeError("Install OpenMed setup dependencies with: pip install -e '.[openmed]'") from exc

  target_dir.mkdir(parents=True, exist_ok=True)
  snapshot_download(
    repo_id=model_id,
    local_dir=str(target_dir),
    allow_patterns=list(DOWNLOAD_ALLOW_PATTERNS),
    local_files_only=local_files_only,
  )
  write_setup_metadata(target_dir, model_id)

  missing = missing_required_files(target_dir)
  if missing:
    raise RuntimeError(f"OpenMed model setup incomplete. Missing: {', '.join(missing)}")
  return target_dir


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    prog="decon-setup-openmed",
    description="Download OpenMed PHI-NER files into the local Decon model cache.",
  )
  parser.add_argument(
    "--model-id",
    default=DEFAULT_MODEL_ID,
    help="Hugging Face model id to download.",
  )
  parser.add_argument(
    "--output-dir",
    help="Explicit model directory. Defaults to the per-user Decon app-data model cache.",
  )
  parser.add_argument(
    "--repo-local",
    action="store_true",
    help="Install into package/local-models for repository-local development.",
  )
  parser.add_argument(
    "--local-files-only",
    action="store_true",
    help="Do not contact the network; only materialize files already in the Hugging Face cache.",
  )
  return parser


def main(argv: Sequence[str] | None = None) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)
  if args.output_dir and args.repo_local:
    parser.error("--output-dir and --repo-local cannot be used together")

  target_dir = resolve_target_dir(
    args.model_id,
    explicit_dir=args.output_dir,
    repo_local=args.repo_local,
  )

  try:
    downloaded_dir = download_model(
      model_id=args.model_id,
      target_dir=target_dir,
      local_files_only=args.local_files_only,
    )
  except RuntimeError as exc:
    parser.exit(1, f"{exc}\n")

  print(f"OpenMed model ready: {downloaded_dir}")
  print("Decon loads this model locally during decontextualization.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

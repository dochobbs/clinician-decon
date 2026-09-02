"""Experimental adapter for Perplexity's local PII masking model.

This module is intentionally outside the supported engine list.  It exists so
the candidate model can be evaluated behind the same deterministic rules and
span-composition policy as the current OpenMed-backed engine without changing
the product default.
"""

from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

from .local_rules import Span
from .openmed_ner import _is_clinical_name_shield, _trim_span


PPLX_MODEL_ID = "perplexity-ai/pplx-pii-masking"
PPLX_MODEL_REVISION = "1e6bb1edd41e03668c6931122be96df893141965"
PPLX_BACKBONE_ID = "perplexity-ai/pplx-embed-v1-0.6b"
PPLX_BACKBONE_REVISION = "2c4d510dd4a732063c31a0f70193e35067b51fd8"
PPLX_REFERENCE_SHA256 = "64f16301fb32ec5dc6a3a1d2b426d11a00b1ca14fef658d2f5d81a845d6e804d"
PPLX_CONFIGURATION_SHA256 = "e914aa73614c91703364c77917313da0821ea04a14d73a7836b5cb40abab1671"
PPLX_MODELING_SHA256 = "baf57b645c7ca3f9e2bd57bd0de82c540c7b455665f1b0ef5ee2f29d60cb8ed5"

PPLX_LABEL_CATEGORIES = {
  "private_person": "name",
  "private_email": "email",
  "private_phone": "phone",
  "private_address": "address",
  "private_url": "url",
  "private_date": "date",
  "account_number": "identifier",
  "secret": "identifier",
  "other_pii": "identifier",
}


class PplxUnavailable(RuntimeError):
  """Raised when the experimental local model cannot be loaded."""


def _category_for_label(label: str) -> str | None:
  return PPLX_LABEL_CATEGORIES.get(label.lower().replace("-", "_"))


def _require_sha256(path: Path, expected: str) -> None:
  if not path.is_file():
    raise PplxUnavailable(f"missing pinned PPLX file: {path}")
  actual = hashlib.sha256(path.read_bytes()).hexdigest()
  if actual != expected:
    raise PplxUnavailable(f"PPLX file does not match pinned revision: {path}")


def _load_reference_module(model_dir: Path) -> Any:
  """Load the decoder shipped with the pinned model snapshot."""
  reference_path = model_dir / "example_usage.py"
  _require_sha256(reference_path, PPLX_REFERENCE_SHA256)
  spec = importlib.util.spec_from_file_location("decon_pplx_reference", reference_path)
  if spec is None or spec.loader is None:
    raise PplxUnavailable(f"could not import official reference decoder: {reference_path}")
  module = importlib.util.module_from_spec(spec)
  sys.modules[spec.name] = module
  spec.loader.exec_module(module)
  return module


def _load_backbone_classes(backbone_code_dir: Path) -> tuple[type, type]:
  """Load the two inspected files from the pinned backbone code snapshot."""
  configuration_path = backbone_code_dir / "configuration.py"
  modeling_path = backbone_code_dir / "modeling.py"
  _require_sha256(configuration_path, PPLX_CONFIGURATION_SHA256)
  _require_sha256(modeling_path, PPLX_MODELING_SHA256)

  package_name = "decon_pplx_backbone"
  package = ModuleType(package_name)
  package.__path__ = [str(backbone_code_dir)]
  sys.modules[package_name] = package

  modules = []
  for short_name, path in (
    ("configuration", configuration_path),
    ("modeling", modeling_path),
  ):
    module_name = f"{package_name}.{short_name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
      raise PplxUnavailable(f"could not import pinned PPLX code: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    modules.append(module)
  return modules[0].PPLXQwen3Config, modules[1].PPLXQwen3Model


class PplxSpanDetector:
  """Load the pinned PPLX checkpoint locally and return Decon-compatible spans.

  The upstream example loads the public backbone checkpoint and then replaces
  every backbone weight.  For an offline, storage-efficient comparison we load
  the pinned backbone *code* from ``backbone_code_dir``, instantiate its config,
  and assign the fine-tuned backbone weights from the PII checkpoint directly.
  """

  def __init__(
    self,
    *,
    model_dir: Path,
    backbone_code_dir: Path,
    device: str = "cpu",
    fix_mistral_regex: bool = False,
  ):
    self.model_dir = model_dir
    self.backbone_code_dir = backbone_code_dir
    self.device = device
    self.fix_mistral_regex = fix_mistral_regex
    self._masker: Any | None = None
    self.last_sensitivity: float | None = None
    self.last_predictions: list[dict[str, object]] = []

  def _load(self) -> Any:
    if self._masker is not None:
      return self._masker
    try:
      import torch
      from safetensors.torch import load_file
      from transformers import AutoTokenizer
    except Exception as exc:  # pragma: no cover - depends on optional runtime
      raise PplxUnavailable("torch, safetensors, and transformers are required") from exc

    model_file = self.model_dir / "model.safetensors"
    if not model_file.is_file():
      raise PplxUnavailable(f"missing PPLX checkpoint: {model_file}")
    if not (self.backbone_code_dir / "modeling.py").is_file():
      raise PplxUnavailable(
        f"missing pinned PPLX backbone code: {self.backbone_code_dir}"
      )

    try:
      reference = _load_reference_module(self.model_dir)
      config_class, model_class = _load_backbone_classes(self.backbone_code_dir)
      tokenizer = AutoTokenizer.from_pretrained(
        self.model_dir,
        local_files_only=True,
        fix_mistral_regex=self.fix_mistral_regex,
      )
      config = config_class.from_pretrained(self.backbone_code_dir, local_files_only=True)
      state = load_file(str(model_file), device="cpu")
      backbone_state = {
        key.removeprefix("backbone."): value
        for key, value in state.items()
        if key.startswith("backbone.")
      }

      # Build in bf16 so the temporary initialized model is the same size as
      # the fine-tuned checkpoint rather than allocating a second fp32 copy.
      previous_dtype = torch.get_default_dtype()
      torch.set_default_dtype(torch.bfloat16)
      try:
        backbone = model_class(config)
      finally:
        torch.set_default_dtype(previous_dtype)
      incompatible = backbone.load_state_dict(
        backbone_state,
        strict=True,
      )
      if incompatible.missing_keys or incompatible.unexpected_keys:
        raise PplxUnavailable(
          "PPLX checkpoint did not match the pinned backbone architecture"
        )
      backbone = backbone.to(self.device).eval()

      masker = object.__new__(reference.PiiMasker)
      masker.device = self.device
      masker.tokenizer = tokenizer
      masker.backbone = backbone
      masker.w_cls = state["token_cls_head.weight"].float().to(self.device)
      masker.b_cls = state["token_cls_head.bias"].float().to(self.device)
      masker.w_sen = state["sensitivity_head.weight"].float().to(self.device)
      masker.b_sen = state["sensitivity_head.bias"].float().to(self.device)
      masker.viterbi = reference.ViterbiDecoder(
        reference.BIOES_LABELS,
        b_bias=float(state["viterbi.b_bias"].item()),
        e_bias=float(state["viterbi.e_bias"].item()),
      )
    except PplxUnavailable:
      raise
    except Exception as exc:  # pragma: no cover - depends on local model files
      raise PplxUnavailable(
        f"could not load local PPLX model from {self.model_dir}"
      ) from exc

    self._masker = masker
    return masker

  def __call__(self, text: str) -> list[Span]:
    predicted, sensitivity = self._load()(text)
    self.last_sensitivity = float(sensitivity)
    self.last_predictions = [
      {
        "label": str(item.label),
        "start": int(item.start),
        "end": int(item.end),
        "text": text[int(item.start):int(item.end)],
        "score": float(item.score),
      }
      for item in predicted
    ]
    spans: list[Span] = []
    for item in predicted:
      category = _category_for_label(str(item.label))
      if category is None:
        continue
      start, end = _trim_span(text, int(item.start), int(item.end))
      if _is_clinical_name_shield(text, start, end):
        continue
      if start < end:
        spans.append(Span(category=category, start=start, end=end))
    return spans

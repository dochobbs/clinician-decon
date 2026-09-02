from pathlib import Path
from types import SimpleNamespace

from decon.pplx_ner import PplxSpanDetector, _category_for_label


def test_pplx_entity_category_mapping():
  assert _category_for_label("private_person") == "name"
  assert _category_for_label("private_address") == "address"
  assert _category_for_label("account_number") == "identifier"
  assert _category_for_label("secret") == "identifier"
  assert _category_for_label("sensitive_health") is None


def test_pplx_detector_maps_spans_and_preserves_clinical_eponyms():
  text = "Daniel Whitfield has Kawasaki disease; email daniel@example.com."
  detector = PplxSpanDetector(
    model_dir=Path("unused"),
    backbone_code_dir=Path("unused"),
  )
  detector._masker = lambda _: (
    [
      SimpleNamespace(label="private_person", start=0, end=16, score=0.9),
      SimpleNamespace(label="private_person", start=21, end=29, score=0.8),
      SimpleNamespace(label="private_email", start=45, end=63, score=0.99),
    ],
    0.875,
  )

  spans = detector(text)

  assert [(span.category, text[span.start:span.end]) for span in spans] == [
    ("name", "Daniel Whitfield"),
    ("email", "daniel@example.com"),
  ]
  assert detector.last_sensitivity == 0.875

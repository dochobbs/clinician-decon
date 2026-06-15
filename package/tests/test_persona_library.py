import json
import re
from pathlib import Path


PERSONA_PATH = Path(__file__).resolve().parents[1] / "data" / "personas" / "v1.json"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def test_persona_library_exists_with_required_sections():
  payload = json.loads(PERSONA_PATH.read_text())

  assert payload["schema_version"] == "1.0"
  assert payload["purpose"]
  assert len(payload["clinician_personas"]) >= 8
  assert len(payload["patient_context_personas"]) >= 12
  assert len(payload["source_channel_personas"]) >= 7
  assert len(payload["perturbation_profiles"]) >= 6


def test_persona_ids_are_unique_and_stable():
  payload = json.loads(PERSONA_PATH.read_text())
  ids = []
  for section in (
    "clinician_personas",
    "patient_context_personas",
    "source_channel_personas",
    "perturbation_profiles",
  ):
    for item in payload[section]:
      ids.append(item["id"])
      assert ID_PATTERN.match(item["id"])

  assert len(ids) == len(set(ids))


def test_personas_have_generation_fields():
  payload = json.loads(PERSONA_PATH.read_text())
  required = {
    "id",
    "name",
    "description",
    "trace_goals",
    "phi_risks",
    "clinical_preservation_risks",
    "archetype_tags",
  }

  for section in ("clinician_personas", "patient_context_personas", "source_channel_personas"):
    for item in payload[section]:
      assert required.issubset(item)
      assert item["trace_goals"]
      assert item["phi_risks"]
      assert item["clinical_preservation_risks"]
      assert item["archetype_tags"]


def test_perturbation_profiles_have_pipeline_fields():
  payload = json.loads(PERSONA_PATH.read_text())

  for item in payload["perturbation_profiles"]:
    required = {
      "id",
      "name",
      "description",
      "applies_to",
      "transformations",
      "failure_modes",
    }
    assert required.issubset(item)
    assert item["applies_to"]
    assert item["transformations"]
    assert item["failure_modes"]

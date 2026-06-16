from decon.openmed_ner import (
  _category_for_entity,
  _is_clinical_name_shield,
  _is_word_fragment,
  _trim_span,
)


def test_openmed_entity_category_mapping():
  assert _category_for_entity("PATIENT_NAME") == "name"
  assert _category_for_entity("street_address") == "address"
  assert _category_for_entity("medical_record_number") == "mrn"
  assert _category_for_entity("not_phi") is None


def test_trim_span_removes_surrounding_whitespace_without_changing_token():
  text = "Freya DOB 3/15/2013 asks about asthma. Omar needs albuterol."

  assert _trim_span(text, 9, 11) == (10, 11)
  assert _trim_span(text, 38, 43) == (39, 43)


def test_word_fragment_filter_identifies_partial_medication_spans():
  text = "Qelbree vs guanfacine for ADHD"

  assert _is_word_fragment(text, 0, 1) is True
  assert _is_word_fragment(text, 11, 14) is True
  assert _is_word_fragment("Freya has asthma", 0, 5) is False


def test_clinical_name_shield_keeps_condition_eponyms_when_openmed_tags_name():
  kawasaki_question = "Could this be Kawasaki?"
  kawasaki_case = "Rare case of Kawasaki we've seen with fever and rash."
  addison_disease = "Screen for Addison disease vs developmental dysplasia."

  assert _is_clinical_name_shield(
    kawasaki_question,
    kawasaki_question.index("Kawasaki"),
    kawasaki_question.index("Kawasaki") + len("Kawasaki"),
  ) is True
  assert _is_clinical_name_shield(
    kawasaki_case,
    kawasaki_case.index("Kawasaki"),
    kawasaki_case.index("Kawasaki") + len("Kawasaki"),
  ) is True
  assert _is_clinical_name_shield(
    addison_disease,
    addison_disease.index("Addison"),
    addison_disease.index("Addison") + len("Addison"),
  ) is True
  assert _is_clinical_name_shield("Freya has asthma", 0, 5) is False

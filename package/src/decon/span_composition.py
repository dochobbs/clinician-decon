"""Deterministic composition of model-detected spans.

Model-backed PHI detectors can return partial entity spans. This module holds
the deterministic rules that complete or constrain those spans before they
enter the decon pipeline.
"""

from __future__ import annotations

import re
from typing import Iterable

from .local_rules import Span


BARE_NAME_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)*"
BARE_NAME_RUN = re.compile(
  rf"^\s*({BARE_NAME_TOKEN}(?:\s+{BARE_NAME_TOKEN})*)[\s.,;:!?]*$"
)

# Function words mark a phrase as a sentence rather than a name paste, so
# expansion is skipped and adjacent clinical text survives ("milo has asthma").
BARE_NAME_SENTENCE_GUARD_TERMS = frozenset({
  "a", "an", "and", "any", "are", "at", "be", "been", "being", "but", "by",
  "call", "called", "caller", "came", "complains", "complaining", "denies",
  "for", "from", "had", "has", "have", "here", "his", "her", "in", "into",
  "is", "it", "its", "needs", "of", "off", "on", "onto", "or", "our",
  "presents", "presenting", "reports", "reporting", "says", "she", "since",
  "that", "the", "their", "them", "then", "there", "these", "they", "this",
  "to", "today", "was", "were", "with", "without", "yesterday",
})

# Symptom, anatomy, age, and disease-class vocabulary marks clinical content
# worth preserving, so a mislabeled model span cannot wipe it ("chest pain",
# "two month old", "bacterial infection"). Severity, laterality, and body-part
# words keep the expansion head from walking through clinical modifiers that
# follow a detected name ("Jean Claude Van Damme severe stomach pain").
BARE_NAME_CLINICAL_GUARD_TERMS = frozenset({
  "abdomen", "ache", "aches", "adolescent", "allergies", "allergy",
  "ankle", "ankles", "anxiety", "arm", "arms", "asthma", "bilateral",
  "belly", "bleeding", "better", "both", "bruise", "burning", "chest",
  "cold", "congestion", "constipation", "constant", "cough", "day", "days",
  "depression", "diarrhea", "disease", "dizzy", "dizziness", "dull",
  "ear", "ears", "eczema", "elbow", "elbows", "eye", "eyes", "fatigue",
  "feet", "fever", "finger", "fingers", "foot", "fracture", "groin", "hand",
  "hands", "head", "headache", "heel", "heels", "hip", "hips", "hurt",
  "hurts", "illness", "improving", "infection", "infant", "injury",
  "insomnia", "intermittent", "itch", "itching", "jaw", "joint", "joints",
  "knee", "knees", "left", "leg", "legs", "mild", "moderate", "month",
  "months", "migraine", "muscle", "muscles", "nausea", "neck", "nose",
  "old", "pain", "persistent", "rash", "reflux", "rib", "ribs", "right",
  "seizure", "severe", "sharp", "shin", "shoulder", "shoulders", "sinus",
  "skin", "sore", "stomach", "sudden", "swelling", "symptoms", "syndrome",
  "teenager", "temple", "temples", "throat", "thigh", "toddler", "tummy",
  "unilateral", "virus", "vomit", "vomiting", "week", "weeks", "wheeze",
  "wheezing", "wrist", "wrists", "year", "years",
})


# A relation or provider lead-in marks caregiver/patient context that must
# survive ("Mother Jennifer reports...", "Sibling Aiden had..."), so runs
# starting with these tokens are never treated as bare name material.
BARE_NAME_LEAD_IN_VETO_TERMS = frozenset({
  "aunt", "auntie", "brother", "caregiver", "cousin", "dad", "daddy",
  "daughter", "doctor", "dr", "father", "friend", "grandma", "grandmother",
  "grandpa", "grandfather", "guardian", "husband", "midwife", "mom", "mama",
  "mommy", "mother", "neighbor", "nephew", "niece", "nurse", "papa",
  "parent", "parents", "partner", "patient", "pta", "sibling", "sister",
  "son", "spouse", "stepdad", "stepmom", "stepparent", "teacher", "uncle",
  "wife",
})


def drop_clinical_eponym_spans(text: str, spans: list[Span]) -> list[Span]:
  """Drop model spans that label a clinical eponym as a name or place.

  Eponyms such as ``Kawasaki`` are also real-world names and cities, so a
  token classifier can tag the disease term as a person or location. The
  detector wrapper shields these already; this deterministic backstop keeps
  the guarantee at the composition boundary for any span source.
  """
  from .openmed_ner import _is_clinical_name_shield
  return [
    span for span in spans
    if span.category == "name" or not _is_clinical_name_shield(text, span.start, span.end)
  ]


def complete_bare_name_spans(text: str, detected_spans: Iterable[Span]) -> list[Span]:
  """Complete a partially detected name run.

  A detector hit anywhere inside a leading run of two or more unguarded
  alphabetic tokens expands to one name span covering that whole run, so a
  partial span cannot approve a leaked surname. The run may be followed by
  sentence punctuation or a guarded clinical tail (``milo north fever``
  becomes ``[NAME] fever``); expansion stops at the first guarded token so
  symptom fragments such as ``chest pain`` and sentences such as ``milo has
  asthma`` stay untouched.
  """
  spans = list(detected_spans)
  match = BARE_NAME_RUN.fullmatch(text)
  if match is None:
    return spans

  run_start, run_end = match.span(1)
  guarded_terms = BARE_NAME_SENTENCE_GUARD_TERMS | BARE_NAME_CLINICAL_GUARD_TERMS
  head_end = run_start
  head_token_count = 0
  for token_match in re.finditer(BARE_NAME_TOKEN, text[run_start:run_end]):
    token = token_match.group(0)
    lowered = token.lower()
    if head_token_count == 0 and lowered in BARE_NAME_LEAD_IN_VETO_TERMS:
      return spans
    if lowered in guarded_terms:
      break
    head_end = run_start + token_match.end()
    head_token_count += 1

  if head_token_count < 2:
    return spans

  def is_head_name_span(span: Span) -> bool:
    return (
      span.category == "name"
      and span.start < head_end
      and span.end > run_start
    )

  if not any(is_head_name_span(span) for span in spans):
    return spans

  return [
    span for span in spans if not is_head_name_span(span)
  ] + [Span(category="name", start=run_start, end=head_end)]

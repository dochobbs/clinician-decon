"""Local deterministic decontextualization for the desktop prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Iterable

from .destinations import build_handoff, render_prompt


@dataclass(frozen=True)
class Span:
  category: str
  start: int
  end: int


@dataclass(frozen=True)
class LocalDeconResult:
  original_length: int
  destination: str
  safe_context: str
  safe_query: str
  destination_prompt: str
  removed_categories: dict[str, int]
  risk_level: str
  risk_reasons: list[str]
  copy_allowed: bool
  open_url: str | None
  action_label: str


AGE_UNITS = r"yo|y/o|yrs?|years? old|months? old|months?|mo"
EXPLICIT_AGE_UNITS = r"yo|y/o|yrs?|years? old|months? old|mo"
LAB_TERMS = r"A1c|HbA1c|INR|TSH|LDH|WBC|platelets?|ferritin|lipase|amylase"
MONTH_TERMS = (
  r"January|February|March|April|May|June|July|August|September|October|November|"
  r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
WEEKDAY_TERMS = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
DOB_LABEL = r"DOB|D\.O\.B\.?|date of birth|birthdate|birthday|born"
RELATION_TERMS = (
  r"Mom|Mama|Mami|Mother|Dad|Papa|Father|Grandma|Grandpa|Aunt|Auntie|Uncle|"
  r"Tia|Tio|Abuela|Abuelo|Wife|Husband|Spouse|Partner|Sister|Brother|Daughter|"
  r"Son|Guardian|Caregiver"
)
STREET_TYPES = (
  r"St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Ln|Lane|Way|Ct|Court|"
  r"Pkwy|Parkway"
)
NAME_TOKEN = (
  r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]+|[A-ZÀ-ÖØ-Þ])"
  r"(?:[-'][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]+)?"
)
NAME_PARTICLES = r"van|von|der|den|de|del|da|la|le|di|du|dos|das"
FULL_NAME = rf"{NAME_TOKEN}(?:\s+(?:(?:{NAME_PARTICLES})\s+)*{NAME_TOKEN}){{1,3}}"
NAME_CUES = (
  r"DOB|MRN|on|has|with|presents|asks?|needs|due|from|is|came|called|wants|"
  r"says|lives|peri-menopausal"
)
CAREGIVER_SUBJECT_TERMS = r"Mom|Mother|Dad|Father|Parent|Caregiver|Guardian|Caller"
CAREGIVER_REPORT_VERBS = (
  r"reports?|reported|says|said|states?|stated|notes?|noted|mentions?|mentioned|"
  r"observes?|observed"
)
PATIENT_NAME_FOLLOWERS = (
  r"had|has|was|is|reported|reports|improved|worse|worsened|needs|started|"
  r"stopped|takes|will|should|could|presented|presents|came|comes|reports"
)
PATIENT_NAME_INTRO_PATTERNS: tuple[re.Pattern[str], ...] = (
  re.compile(rf"\b({NAME_TOKEN})\s+(?i:is\s+a\s+patient)\b"),
  re.compile(rf"\b({NAME_TOKEN})\s+(?i:returns\s+for\s+(?:follow-up|followup))\b"),
  re.compile(
    rf"\b({NAME_TOKEN})\s+(?i:(?:presents|presented|came|comes))\b",
  ),
  re.compile(rf"\b({NAME_TOKEN})\s+(?i:was\s+seen)\b"),
  re.compile(rf"\b({NAME_TOKEN})'s\s+(?i:(?:mother|mom|father|parent|caregiver))\b"),
  re.compile(
    rf"\b(?i:(?:mother|mom|father|parent|caregiver)\s+reports)\s+({NAME_TOKEN})\b",
  ),
  re.compile(
    rf"\b(?i:(?:{CAREGIVER_SUBJECT_TERMS}))(?:\s+{NAME_TOKEN})?\s+"
    rf"(?i:(?:{CAREGIVER_REPORT_VERBS}))\s+({NAME_TOKEN})"
    rf"(?=(?:'s)?\s+(?i:{PATIENT_NAME_FOLLOWERS})\b)",
  ),
  re.compile(rf"\b(?i:(?:the|this)\s+patient)\s+({NAME_TOKEN})\b"),
  re.compile(
    rf"\b(?i:(?:follow-up|followup|assessment|hpi|history|subjective))\s*:\s*({NAME_TOKEN})"
    r"(?=\s+(?i:had|has|reports|reported|was|is|returns|presents|presented|came|comes)\b)",
  ),
)
EPONYM_FOLLOWERS = r"syndrome|disease|criteria|sign|triad|classification|test"

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("prompt_injection", re.compile(
    r"\b(?:system|developer|admin(?:istrator)?)\s+"
    r"(?:update|message|override|instruction)\s*:\s*[^.?!]*(?:[.?!]|$)",
    re.IGNORECASE,
  )),
  ("prompt_injection", re.compile(
    r"\badministrator\s+override\s+code\s+[A-Z0-9-]+\b\.?",
    re.IGNORECASE,
  )),
  ("prompt_injection", re.compile(
    r"\b(?:include|return|preserve)\s+(?:all\s+)?patient details\b[^.?!]*(?:[.?!]|$)",
    re.IGNORECASE,
  )),
  ("prompt_injection", re.compile(
    r"\b(?:ignore|disregard|override)\s+(?:your\s+|all\s+)?(?:previous|prior|above)\s+"
    r"instructions\b[^.?!]*(?:[.?!]|$)",
    re.IGNORECASE,
  )),
  ("contextual_identifier", re.compile(r"\bonly case\b", re.IGNORECASE)),
  ("address", re.compile(
    rf"\b\d{{1,6}}\s+(?:[A-Za-z0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?",
    re.IGNORECASE,
  )),
  ("address", re.compile(r"\b(?:Apt|Apartment|Unit|Suite|Ste|#)\s*[A-Z0-9-]+\b", re.IGNORECASE)),
  ("location", re.compile(
    rf"\b(?i:(?:lives?|resides|located)\s+(?:at|in))\s+"
    rf"\d{{1,6}}\s+(?:[A-Za-z0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?,\s*"
    rf"({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})\b",
  )),
  ("location", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2},\s*[A-Z]{2}\b")),
  ("location", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b")),
  ("location", re.compile(
    rf"\b(?i:(?:from|near|in|at))\s+({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})"
    r"(?=\s*(?:[-,.;:)]|$))",
  )),
  ("zip", re.compile(r"\b(?:ZIP|zip code)\s*[:#]?\s*(\d{5}(?:-\d{4})?)\b", re.IGNORECASE)),
  ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("email", re.compile(
    r"\bemail\s+([A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+"
    r"(?:\s+(?:dot\s+)?[A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+){0,10}\s+at\s+"
    r"[A-Za-z0-9]+(?:\s+dot\s+[A-Za-z]{2,})+)\b",
    re.IGNORECASE,
  )),
  ("email", re.compile(
    r"\b([A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+"
    r"(?:\s+dot\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+){1,10}\s+at\s+"
    r"[A-Za-z0-9]+(?:\s+dot\s+[A-Za-z]{2,})+)\b",
    re.IGNORECASE,
  )),
  ("phone", re.compile(r"(?:\+1[\s-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  ("phone", re.compile(r"\b((?:\d\s+){9}\d)\b")),
  ("phone", re.compile(
    r"\b(?:callback|contact|phone|call|text)\s+((?:\d\s*){10})\b",
    re.IGNORECASE,
  )),
  ("ssn", re.compile(
    r"\b(?:SSN|Social[\s-]?Security[\s-]?(?:Number|#)?)\s*[:#]?\s*"
    r"(\d{3}[-\s]?\d{2}[-\s]?\d{4}|\d{9})\b",
    re.IGNORECASE,
  )),
  ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  ("identifier", re.compile(
    r"\b(?:chart|account|acct|policy|member|subscriber|insurance policy)\s*"
    r"(?:number|no\.?|id|#)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{5,})\b",
    re.IGNORECASE,
  )),
  ("identifier", re.compile(
    r"\b(?:driver'?s?\s+license|license|certificate|cert(?:ificate)?|device|serial)\s*"
    r"(?:number|no\.?|id|#)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{5,})\b",
    re.IGNORECASE,
  )),
  ("mrn", re.compile(
    r"\b(?:patient number|patient no\.?|patient #|pt number)\s*"
    r"([A-Z0-9][A-Z0-9-]{3,})\b",
    re.IGNORECASE,
  )),
  ("mrn", re.compile(r"\bM\s+R\s+N\s+((?:[A-Z0-9]\s+){5,19}[A-Z0-9])\b", re.IGNORECASE)),
  ("mrn", re.compile(r"\b(?:MRN|MR#|medical record(?: number)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,})\b", re.IGNORECASE)),
  ("mrn", re.compile(r"\b[A-Z]{1,5}-\d{3,8}(?:-\d{3,8})?\b")),
  ("ip_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
  ("url", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
  ("pharmacy", re.compile(
    rf"\b(?:Walgreens|CVS|Rite Aid|Walmart Pharmacy|Costco Pharmacy|Kroger Pharmacy)"
    rf"\s+(?:on|at|in)\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}"
    rf"(?:\s+in\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})?\b",
    re.IGNORECASE,
  )),
  ("school", re.compile(
    rf"\b(?:{NAME_TOKEN}\s+){{1,4}}(?:Elementary|Middle|High)\s+School\b",
    re.IGNORECASE,
  )),
  ("school", re.compile(
    rf"\b(?:{NAME_TOKEN}\s+){{1,4}}(?:School|Academy)\b",
    re.IGNORECASE,
  )),
  ("camp", re.compile(rf"\bCamp\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}\b")),
  ("practice", re.compile(
    r"\b(?:Lakes\s+Pediatrics|Children['’]s(?:\s+Hospital)?|Mayo\s+Clinic|Cleveland\s+Clinic|"
    r"[A-Z][A-Za-z'’.-]+\s+(?:Pediatrics|Clinic|Hospital|Family Medicine|Medical Group|"
    r"Health|Urgent Care))\b",
    re.IGNORECASE,
  )),
  ("insurance", re.compile(
    r"\b(?:Blue\s+Cross|BCBS|Aetna|Cigna|UnitedHealth(?:care)?|Kaiser|Humana|"
    r"Anthem|Medicaid|Medicare|Tricare)\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b")),
  ("date", re.compile(
    r"\b(?:today|yesterday|last\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(
    rf"\b(?:(?:next|this|last)\s+)?(?:{WEEKDAY_TERMS})\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(
    rf"\b(?:{MONTH_TERMS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,)?\s+\d{{4}}\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTH_TERMS})\.?\s+\d{{4}}\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(rf"\b(?:{MONTH_TERMS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.IGNORECASE)),
  ("date", re.compile(r"\blast\s+week\b", re.IGNORECASE)),
  ("body_measurement", re.compile(r"\bBMI\s*\d{1,2}(?:\.\d+)?\b", re.IGNORECASE)),
  ("body_measurement", re.compile(r"\b\d{2,3}\s*(?:lbs?|kg|pounds?)\b", re.IGNORECASE)),
  ("body_measurement", re.compile(r"\b\d{1,2}'\s*\d{1,2}\"|\b\d{1,2}\s*ft\s*\d{1,2}\s*in\b", re.IGNORECASE)),
  ("clinical_value", re.compile(
    rf"\b(?:{LAB_TERMS})\s*(?:came\s+back\s+at|was|were|is|of|at|[:=])?\s*"
    r"\d[\d.,]*(?:k)?\b",
    re.IGNORECASE,
  )),
  ("age", re.compile(r"\b\d{1,3}\s*(?:M|F)\b", re.IGNORECASE)),
  ("age", re.compile(rf"\b(?:he'?s|she'?s|patient is|pt is)\s+(\d{{1,3}}\s+months?)\b", re.IGNORECASE)),
  ("age", re.compile(r"\b\d{1,3}-year-olds?\b", re.IGNORECASE)),
  ("age", re.compile(rf"\b\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b", re.IGNORECASE)),
  ("relation", re.compile(
    r"\b(?:the\s+)?(?:twins'?|siblings'?)\s+(?:older|younger|baby|little)?\s*"
    r"(?:brother|sister|sibling|kid|child)\b",
    re.IGNORECASE,
  )),
  ("nickname", re.compile(r"\b(?i:(?:Lil|Little|Big|Lil'))\s+(?:[A-Z](?:\.|\b)|[A-Z][a-z]{1,3})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:La\s+mam[aá]|El\s+pap[aá]|Mi\s+hij[oa]|Su\s+hij[oa]|El\s+paciente|"
    rf"La\s+paciente)\s+(?:de\s+)?({FULL_NAME})(?=,|\b))"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:La\s+mam[aá]|El\s+pap[aá]|Mi\s+hij[oa]|Su\s+hij[oa])\s+de\s+"
    rf"{FULL_NAME},\s*)({NAME_TOKEN})(?=,\s*dice\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:La\s+mam[aá]|El\s+pap[aá]|Mi\s+hij[oa]|Su\s+hij[oa]|El\s+paciente|"
    rf"La\s+paciente)\s+(?:de\s+)?({NAME_TOKEN})\b)",
  )),
  ("name", re.compile(
    rf'"(?i:patient_name)"\s*:\s*"({FULL_NAME})"'
  )),
  ("name", re.compile(
    rf"\b(?i:(?:preferred\s+name|patient\s+name|name))\s*[:#-]\s*({FULL_NAME}|{NAME_TOKEN})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:patient\s+named)\s+({FULL_NAME}|{NAME_TOKEN})"
    rf"(?=\s+(?i:{PATIENT_NAME_FOLLOWERS})\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:caller)\s+({NAME_TOKEN})(?=\s+at\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:caller|caregiver|guardian))\s+({NAME_TOKEN})"
    rf"(?=\s+(?i:(?:{CAREGIVER_REPORT_VERBS}|at|callback|called))\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:sibling)\s+({NAME_TOKEN})(?=\s+(?:is|was|has|had|needs|worried|worries)\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:the\s+)?patient\s+(?:I'?m|I\s+am)\s+asking\s+about\s+is)\s+"
    rf"({FULL_NAME})\b",
  )),
  ("name", re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+({NAME_TOKEN})(?='s\b|\b)")),
  ("name", re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+({FULL_NAME})\b")),
  ("name", re.compile(rf"\b(?i:(?:{RELATION_TERMS}))\s+({NAME_TOKEN})\b")),
  ("name", re.compile(rf"\b(?i:(?:{RELATION_TERMS}))\s+\(({NAME_TOKEN})\)(?=\W|$)")),
  ("name", re.compile(rf"\b(?i:little)\s+({NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:SUBJECTIVE|HPI|CC|HISTORY|ASSESSMENT))\s*:\s*({FULL_NAME})"
    r"(?=\s*(?:,|\d))",
  )),
  ("name", re.compile(
    rf"\b(?i:(?:Patient|Pt))\s+({NAME_TOKEN})"
    r"(?=\s+(?:has|presents|needs|asks|is|was|reports|states)\b)",
  )),
  ("name", re.compile(
    rf"\b(?i:(?:should|can|could|would))\s+({NAME_TOKEN})"
    r"(?=\s+(?:get|receive|take|start|use)\b)",
  )),
  ("name", re.compile(
    rf"\b(?i:(?:patient number|patient no\.?|patient #|pt number))\s+"
    rf"[A-Z0-9-]+,\s*({FULL_NAME})(?=,\s*(?i:(?:date of birth|DOB))\b)",
  )),
  ("name", re.compile(
    rf"^(?!(?:{RELATION_TERMS}|Caller)\b)({NAME_TOKEN})"
    r"(?=\s+(?:has|presents|needs|asks|is|was|reports|states)\b)"
  )),
  ("name", re.compile(rf"\b(?:calls?\s+(?:him|her|them)|known\s+as|nicknamed)\s+({NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:Pt|Patient|Family of|chart for|for patient|for pt))\s+({FULL_NAME})"
    rf"(?=\s*(?:,|\(|\b(?i:(?:{NAME_CUES}))\b|\d{{1,3}}\s*(?:M|F)\b|\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b))",
  )),
  ("name", re.compile(
    rf"\b({NAME_TOKEN})\s+\(\s*\d{{1,3}}\s*(?:M|F|{EXPLICIT_AGE_UNITS})\s*\)",
  )),
  ("name", re.compile(
    rf"^({FULL_NAME})(?=\s*(?:,|\(|\b(?i:(?:{NAME_CUES}))\b|\d{{1,3}}\s*(?:M|F)\b|"
    rf"\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b))"
  )),
  ("name", re.compile(
    rf"\b(?!(?:{RELATION_TERMS})\s)"
    rf"({FULL_NAME})\s+"
    rf"(?:DOB|MRN|came|asks?|called|has|with|was|seen|presents|needs|"
    rf"\d{{1,3}}\s*(?:{AGE_UNITS}))\b"
  )),
  ("name", re.compile(
    rf"\b({FULL_NAME}),\s+\d{{1,2}}\s+weeks\s+pregnant\b"
  )),
)

RESIDUAL_HIGH_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible MRN or record identifier remains", re.compile(r"\b(?:MRN|MR#)\s+[A-Z0-9-]{6,}\b", re.IGNORECASE)),
  ("possible MRN or record identifier remains", re.compile(
    r"\brecord\s+(?!(?:number|id|identifier)\b)[A-Z0-9-]{6,}\b",
    re.IGNORECASE,
  )),
  ("possible MRN or record identifier remains", re.compile(
    r"\brecord\s+(?:number|id|identifier)\s+(?=[A-Z0-9-]*\d)[A-Z0-9-]{6,}\b",
    re.IGNORECASE,
  )),
  ("possible ZIP code remains", re.compile(r"\b(?:ZIP|zip code)\s*[:#]?\s*\d{5}(?:-\d{4})?\b", re.IGNORECASE)),
  ("possible email remains", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("possible phone remains", re.compile(r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b")),
  ("possible SSN remains", re.compile(r"\b(?:SSN|Social Security)\s*[:#]?\s*(?:\d{3}-\d{2}-\d{4}|\d{9})\b", re.IGNORECASE)),
  ("possible SSN remains", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
  ("possible patient URL remains", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
  ("possible prompt injection remains", re.compile(r"\b(?:ignore|disregard|override)\s+(?:previous|prior|above)\s+instructions\b", re.IGNORECASE)),
  ("possible city/state location remains", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2},\s*[A-Z]{2}\b")),
  ("possible practice or facility remains", re.compile(r"\b[A-Z][A-Za-z'’.-]+\s+(?:Pediatrics|Clinic|Hospital|Medical Group|Health|Urgent Care)\b")),
)

RESIDUAL_MEDIUM_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible exact date remains", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
  ("possible direct name remains", re.compile(r"\b(?:Mr|Mrs|Ms|Miss)\.?\s+[A-Z][a-z]{2,}\b")),
  ("possible patient name remains", re.compile(
    rf"\b(?:Pt|Patient|Family of|chart for|for patient|for pt)\s+{FULL_NAME}\b",
    re.IGNORECASE,
  )),
)

QUERY_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
  re.compile(r"\b(?:DOB|D\.O\.B\.?|MRN|MR#|OCR export|callback|email)\b", re.IGNORECASE),
  re.compile(
    r"\b(?:came in|called from|asking|asks?|today|at this age|before I paste into the LLM|"
    r"routine vaccine question)\b",
    re.IGNORECASE,
  ),
  re.compile(r"\b(?:he|she|his|her|him|mom|mother|dad|father)\b", re.IGNORECASE),
)

RELATION_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
  (re.compile(r"\b(?:Mom|Mother|Dad|Father)\s+\[NAME\]", re.IGNORECASE), "parent"),
  (re.compile(r"\b(?:Mom|Mother|Dad|Father)\s+\(\[NAME\]\)", re.IGNORECASE), "parent"),
  (re.compile(r"\b(?:La\s+mam[aá]|El\s+pap[aá])\s+de\s+\[NAME\]", re.IGNORECASE), "parent"),
  (re.compile(r"\blittle\s+\[NAME\]", re.IGNORECASE), "child"),
  (re.compile(r"\b(?:Wife|Husband|Spouse|Partner)\s+\[NAME\]", re.IGNORECASE), "spouse"),
  (re.compile(r"\b(?:Sister|Brother)\s+\[NAME\]", re.IGNORECASE), "sibling"),
  (re.compile(r"\bsibling\s+\[NAME\]", re.IGNORECASE), "sibling"),
  (re.compile(r"\b(?:Daughter|Son)\s+\[NAME\]", re.IGNORECASE), "child"),
  (re.compile(r"\b(?:Grandma|Grandpa)\s+\[NAME\]", re.IGNORECASE), "grandparent"),
  (re.compile(r"\b(?:Guardian|Caregiver)\s+\[NAME\]", re.IGNORECASE), "caregiver"),
  (re.compile(r"\b(?:Aunt|Uncle)\s+\[NAME\]", re.IGNORECASE), "relative"),
)

DATE_FORMATS = (
  "%m/%d/%Y",
  "%m/%d/%y",
  "%m-%d-%Y",
  "%m-%d-%y",
  "%m.%d.%Y",
  "%m.%d.%y",
  "%Y-%m-%d",
  "%B %d, %Y",
  "%b %d, %Y",
  "%B %d %Y",
  "%b %d %Y",
  "%d %B %Y",
  "%d %b %Y",
)


def _collect_spans(text: str) -> list[Span]:
  spans: list[Span] = []
  for category, pattern in PATTERNS:
    for match in pattern.finditer(text):
      if match.lastindex:
        start, end = match.span(match.lastindex)
      else:
        start, end = match.span(0)
      if start != end:
        spans.append(Span(category=category, start=start, end=end))
  spans.extend(_propagated_patient_name_spans(text))
  return _select_non_overlapping(spans)


def _propagated_patient_name_spans(text: str) -> list[Span]:
  names = _introduced_patient_names(text)
  spans = []
  for name in names:
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])")
    for match in pattern.finditer(text):
      if _is_clinical_eponym_context(text, match.end()):
        continue
      spans.append(Span(category="name", start=match.start(), end=match.end()))
  return spans


def _introduced_patient_names(text: str) -> tuple[str, ...]:
  names: list[str] = []
  for pattern in PATIENT_NAME_INTRO_PATTERNS:
    for match in pattern.finditer(text):
      name = match.group(1)
      if re.fullmatch(rf"(?i)(?:{RELATION_TERMS})", name):
        continue
      if name not in names:
        names.append(name)
  return tuple(names)


def _is_clinical_eponym_context(text: str, end: int) -> bool:
  after = text[end:end + 32].lstrip()
  return bool(re.match(rf"(?i)(?:{EPONYM_FOLLOWERS})\b", after))


def _select_non_overlapping(spans: Iterable[Span]) -> list[Span]:
  selected: list[Span] = []
  last_end = -1
  for span in sorted(spans, key=lambda item: (item.start, -(item.end - item.start))):
    if span.start >= last_end:
      selected.append(span)
      last_end = span.end
  return selected


def _apply_spans(text: str, spans: list[Span], reference_date: date) -> tuple[str, dict[str, int]]:
  safe = text
  counts: dict[str, int] = {}
  for span in sorted(spans, key=lambda item: item.start, reverse=True):
    counts[span.category] = counts.get(span.category, 0) + 1
    replacement = _replacement_for_span(text, span, reference_date)
    safe = safe[:span.start] + replacement + safe[span.end:]
  safe = _normalize_safe_context(safe)
  safe = re.sub(r"\s+", " ", safe).strip()
  return safe, dict(sorted(counts.items()))


def _replacement_for_span(text: str, span: Span, reference_date: date) -> str:
  raw = text[span.start:span.end]
  if span.category == "prompt_injection":
    return ""
  if span.category == "contextual_identifier":
    return "Rare case"
  if span.category == "relation":
    return "sibling contact"
  if span.category == "age":
    return _normalize_age(raw)
  if span.category == "body_measurement":
    return _generalize_body_measurement(raw, text, span)
  if span.category == "pharmacy":
    return "pharmacy"
  if span.category == "school":
    return _generalize_school(raw)
  if span.category == "camp":
    return "camp"
  if span.category == "clinical_value":
    return _generalize_clinical_value(raw)
  if span.category == "date":
    derived_age = _derive_age_for_date(text, span, reference_date)
    if derived_age:
      return derived_age
    return _generalize_date(raw)
  return f"[{span.category.upper()}]"


def _normalize_safe_context(text: str) -> str:
  safe = text
  safe = re.sub(r"\[NAME\]'s\b", "patient's", safe)
  safe = re.sub(r"\bBoth\s+\[NAME\]\s+and\s+(?:his|her|their)\s+mother\b", "Both patient and mother", safe, flags=re.IGNORECASE)
  safe = re.sub(
    rf"\b(?:{DOB_LABEL})\s*[:#.-]?\s*(?=(?:newborn|\d{{1,2}}-month-old|\d{{1,3}}-year-old|90 or older)\b)",
    "",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(r"\b(?:MRN|MR#)\s+\[MRN\]", "[MRN]", safe, flags=re.IGNORECASE)
  safe = re.sub(r"\bSSN\s+\[SSN\]", "[SSN]", safe, flags=re.IGNORECASE)
  for pattern, replacement in RELATION_REPLACEMENTS:
    safe = pattern.sub(replacement, safe)
  safe = re.sub(r"\s+([,.;:])", r"\1", safe)
  return safe


def _normalize_age(raw: str) -> str:
  hyphen_year_match = re.search(
    r"\b(?P<amount>\d{1,3})-year-olds?\b",
    raw,
    flags=re.IGNORECASE,
  )
  if hyphen_year_match:
    amount = int(hyphen_year_match.group("amount"))
    if amount >= 90:
      return "90 or older"
    return f"{amount}-year-old"
  compact_match = re.search(
    r"\b(?P<amount>\d{1,3})\s*(?P<sex>M|F)\b",
    raw,
    flags=re.IGNORECASE,
  )
  if compact_match:
    amount = int(compact_match.group("amount"))
    sex = "male" if compact_match.group("sex").lower() == "m" else "female"
    if amount >= 90:
      return f"90 or older {sex}"
    return f"{amount}-year-old {sex}"
  match = re.search(
    rf"\b(?P<amount>\d{{1,3}})\s*(?P<unit>{AGE_UNITS})\b",
    raw,
    flags=re.IGNORECASE,
  )
  if not match:
    return "[AGE]"
  amount = int(match.group("amount"))
  unit = match.group("unit").lower()
  if unit in ("mo", "month", "months", "month old", "months old"):
    return f"{amount}-month-old"
  if amount >= 90:
    return "90 or older"
  return f"{amount}-year-old"


def _parse_date(raw: str) -> date | None:
  normalized = re.sub(r"(\d{1,2})(?:st|nd|rd|th)", r"\1", raw, flags=re.IGNORECASE)
  for date_format in DATE_FORMATS:
    try:
      return datetime.strptime(normalized, date_format).date()
    except ValueError:
      continue
  return None


def _age_from_dob(dob: date, reference_date: date) -> str | None:
  if dob > reference_date:
    return None
  years = reference_date.year - dob.year
  if (reference_date.month, reference_date.day) < (dob.month, dob.day):
    years -= 1
  if years >= 90:
    return "90 or older"
  if years >= 2:
    return f"{years}-year-old"
  months = (reference_date.year - dob.year) * 12 + reference_date.month - dob.month
  if reference_date.day < dob.day:
    months -= 1
  if months <= 0:
    return "newborn"
  return f"{months}-month-old"


def _derive_age_for_date(text: str, span: Span, reference_date: date) -> str | None:
  context = text[max(0, span.start - 24):span.start].lower()
  if not re.search(rf"\b(?:{DOB_LABEL})\b", context, re.IGNORECASE):
    return None
  parsed = _parse_date(text[span.start:span.end])
  if parsed is None:
    return None
  return _age_from_dob(parsed, reference_date)


def _extract_safe_age(source: str, reference_date: date) -> str | None:
  compact_age = re.search(r"\b\d{1,3}\s*(?:M|F)\b", source, flags=re.IGNORECASE)
  if compact_age:
    return _normalize_age(compact_age.group(0))
  hyphen_year_age = re.search(r"\b\d{1,3}-year-olds?\b", source, flags=re.IGNORECASE)
  if hyphen_year_age:
    return _normalize_age(hyphen_year_age.group(0))
  contextual_month_age = re.search(
    r"\b(?:he'?s|she'?s|patient is|pt is)\s+(\d{1,3}\s+months?)\b",
    source,
    flags=re.IGNORECASE,
  )
  if contextual_month_age:
    return _normalize_age(contextual_month_age.group(1))
  explicit_age = re.search(
    rf"\b\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b",
    source,
    flags=re.IGNORECASE,
  )
  if explicit_age:
    return _normalize_age(explicit_age.group(0))
  dob_match = re.search(
    rf"\b(?:{DOB_LABEL})\s*[:#.-]?\s*"
    rf"(\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|\d{{4}}-\d{{1,2}}-\d{{1,2}}|"
    rf"(?:{MONTH_TERMS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,)?\s+\d{{4}}|"
    rf"\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTH_TERMS})\.?\s+\d{{4}})\b",
    source,
    flags=re.IGNORECASE,
  )
  if dob_match:
    parsed = _parse_date(dob_match.group(1))
    if parsed:
      return _age_from_dob(parsed, reference_date)
  return None


def _is_pediatric_age(age: str | None) -> bool:
  if age is None:
    return False
  if age == "newborn" or "month-old" in age:
    return True
  match = re.match(r"(\d{1,3})-year-old", age)
  return bool(match and int(match.group(1)) < 18)


def _generalize_date(raw: str) -> str:
  lowered = raw.lower()
  if lowered == "today":
    return "same-day"
  if lowered == "yesterday":
    return "1 day prior"
  if lowered.startswith("last "):
    return "recent"
  return "[DATE]"


def _generalize_clinical_value(raw: str) -> str:
  match = re.search(
    rf"\b(?P<label>{LAB_TERMS})\s*(?:came\s+back\s+at|was|were|is|of|at|[:=])?\s*"
    r"(?P<value>\d[\d.,]*(?:k)?)\b",
    raw,
    re.IGNORECASE,
  )
  if not match:
    return "[CLINICAL_VALUE]"
  label = match.group("label")
  normalized_label = "A1c" if label.lower() in ("a1c", "hba1c") else label.upper()
  value_text = match.group("value").replace(",", "").lower()
  multiplier = 1000 if value_text.endswith("k") else 1
  value_text = value_text.removesuffix("k")
  try:
    value = float(value_text) * multiplier
  except ValueError:
    return f"{normalized_label} value"
  if normalized_label == "A1c":
    if value >= 6.5:
      return "elevated A1c"
    return "A1c value"
  if normalized_label == "TSH":
    if value > 4.5:
      return "elevated TSH"
    if value < 0.4:
      return "low TSH"
    return "TSH value"
  if normalized_label in ("FERRITIN", "WBC", "PLATELETS", "LDH"):
    label_display = {
      "FERRITIN": "Ferritin",
      "WBC": "WBC",
      "PLATELETS": "platelets",
      "LDH": "LDH",
    }[normalized_label]
    return f"{label_display} {match.group('value')}"
  return f"{normalized_label} value"


def _generalize_body_measurement(raw: str, text: str, span: Span) -> str:
  context = text[max(0, span.start - 80):min(len(text), span.end + 120)]
  if (
    re.search(r"\b\d{2,3}\s*(?:lbs?|kg|pounds?)\b", raw, re.IGNORECASE)
    and re.search(
      r"\b(?:weighs?|dose|dosing|mg/kg|epinephrine|autoinjector|amoxicillin|"
      r"weight-based)\b",
      context,
      re.IGNORECASE,
    )
  ):
    return raw.strip()
  bmi_match = re.search(r"\bBMI\s*(?P<value>\d{1,2}(?:\.\d+)?)\b", raw, re.IGNORECASE)
  if bmi_match:
    value = float(bmi_match.group("value"))
    if value >= 30:
      return "obesity-range BMI"
    if value >= 25:
      return "overweight-range BMI"
    return "BMI value"
  if re.search(r"\b\d{1,2}'\s*\d{1,2}\"|\b\d{1,2}\s*ft\s*\d{1,2}\s*in\b", raw, re.IGNORECASE):
    return "height value"
  if re.search(r"\b\d{2,3}\s*(?:lbs?|kg|pounds?)\b", raw, re.IGNORECASE):
    return "weight value"
  return "[BODY_MEASUREMENT]"


def _generalize_school(raw: str) -> str:
  lowered = raw.lower()
  if "middle school" in lowered:
    return "middle school"
  if "high school" in lowered:
    return "high school"
  if "elementary" in lowered:
    return "elementary school"
  return "school"


def _safe_query_from_context(safe_context: str) -> str:
  query = re.sub(r"\[[A-Z_]+\]", " ", safe_context)
  for pattern in QUERY_NOISE_PATTERNS:
    query = pattern.sub(" ", query)
  query = re.sub(r"\s+", " ", query).strip(" ,.;:-")
  return query or "de-identified clinical question"


def _safe_query_from_text(source: str, safe_context: str, reference_date: date) -> str:
  lower_source = source.lower()
  safe_age = _extract_safe_age(source, reference_date) or _extract_safe_age(safe_context, reference_date)
  age_prefix = f"{safe_age} " if safe_age else ""
  pediatric_label = "pediatric " if safe_age is None or _is_pediatric_age(safe_age) else ""
  if re.search(
    r"\b(?:under-immunized|under immunized|catch-up|siblings?|separate shots|adhd)\b",
    lower_source,
  ):
    return _safe_query_from_context(safe_context)
  if re.search(r"\b(?:hpv|human papillomavirus)\b", lower_source):
    return f"{age_prefix}{pediatric_label}HPV vaccine schedule current guidelines".strip()
  if re.search(r"\b(?:vaccine|vaccines|vaccination|immunization|shots)\b", lower_source):
    return f"{age_prefix}{pediatric_label}immunization schedule vaccines current guidelines".strip()
  return _safe_query_from_context(safe_context)


def _risk(safe_context: str) -> tuple[str, list[str]]:
  high_reasons = [reason for reason, pattern in RESIDUAL_HIGH_RISK if pattern.search(safe_context)]
  if high_reasons:
    return "high", high_reasons
  medium_reasons = [reason for reason, pattern in RESIDUAL_MEDIUM_RISK if pattern.search(safe_context)]
  if medium_reasons:
    return "medium", medium_reasons
  return "low", []


def decontextualize_text(
  text: str,
  *,
  destination: str,
  reference_date: date | None = None,
) -> LocalDeconResult:
  """Run local rule-based decontextualization and render destination handoff data."""
  source = text.strip()
  ref_date = reference_date or date.today()
  spans = _collect_spans(source)
  safe_context, removed_categories = _apply_spans(source, spans, ref_date)
  safe_query = _safe_query_from_text(source, safe_context, ref_date)
  risk_level, risk_reasons = _risk(safe_context)
  destination_prompt = render_prompt(destination, safe_context=safe_context, safe_query=safe_query)
  handoff = build_handoff(destination, destination_prompt)
  return LocalDeconResult(
    original_length=len(source),
    destination=destination,
    safe_context=safe_context,
    safe_query=safe_query,
    destination_prompt=destination_prompt,
    removed_categories=removed_categories,
    risk_level=risk_level,
    risk_reasons=risk_reasons,
    copy_allowed=risk_level != "high",
    open_url=handoff.open_url,
    action_label=handoff.action_label,
  )

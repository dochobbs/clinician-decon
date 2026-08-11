"""Local deterministic decontextualization for the desktop prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Callable, Iterable

from .destinations import build_handoff, render_prompt


@dataclass(frozen=True)
class Span:
  category: str
  start: int
  end: int


SpanDetector = Callable[[str], Iterable[Span]]


@dataclass(frozen=True)
class LocalDeconResult:
  original_length: int
  destination: str
  safe_context: str
  safe_query: str
  destination_prompt: str
  removed_categories: dict[str, int]
  removed_spans: list[dict[str, int | str]]
  risk_level: str
  risk_reasons: list[str]
  copy_allowed: bool
  open_url: str | None
  action_label: str
  engine: str
  engine_requested: str
  engine_fallback_reason: str


LOCAL_RULES_ENGINE = "local-rules"
OPENMED_ENGINE = "rules+openmed"
AUTO_ENGINE = "auto"
SUPPORTED_ENGINES = {AUTO_ENGINE, LOCAL_RULES_ENGINE, OPENMED_ENGINE}
REVIEW_SPAN_CATEGORIES = {"date", "location", "pharmacy", "school", "camp"}


AGE_UNITS = r"yo|y/o|yrs?|years? old|months? old|months?|mo"
EXPLICIT_AGE_UNITS = r"yo|y/o|yrs?|years? old|months? old|mo"
SAFE_AGE_PHRASES = (
  "newborn",
  "infant under 6 months",
  "infant 6-11 months",
  "toddler 12-23 months",
  "preschool child",
  "school-age child",
  "early adolescent",
  "adolescent",
  "adult 18-44",
  "adult 45-64",
  "older adult 65-74",
  "older adult 75-89",
  "adult age 90 or older",
)
SAFE_AGE_PATTERN = "|".join(re.escape(phrase) for phrase in SAFE_AGE_PHRASES)
LAB_TERMS = r"A1c|HbA1c|INR|TSH|LDH|WBC|platelets?|ferritin|lipase|amylase"
MONTH_TERMS = (
  r"January|February|March|April|May|June|July|August|September|October|November|"
  r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|März|Maerz|Marz"
)
WEEKDAY_TERMS = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
DOB_LABEL = r"DOB|D\.O\.B\.?|date of birth|birthdate|birthday|born"
RELATION_TERMS = (
  r"Mom|Mama|Mami|Mother|Dad|Papa|Father|Grandma|Grandpa|Aunt|Auntie|Uncle|"
  r"Tia|Tio|Abuela|Abuelo|Wife|Husband|Spouse|Partner|Sister|Brother|Daughter|"
  r"Son|Guardian|Caregiver|MOC|FOC"
)
STREET_TYPES = (
  r"St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Ln|Lane|Way|Ct|Court|"
  r"Pkwy|Parkway|Calle"
)
US_STATE_ABBR = (
  r"AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|"
  r"MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA|VT|"
  r"WA|WI|WV|WY|DC|AS|GU|MP|PR|VI"
)
NAME_TOKEN = (
  r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]+|[A-ZÀ-ÖØ-Þ])"
  r"(?:[-'][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]+)?"
)
BARE_NAME_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)*"
BARE_TWO_TOKEN_NAME = re.compile(rf"^\s*({BARE_NAME_TOKEN}\s+{BARE_NAME_TOKEN})\s*$")
LABEL_NAME_VALUE = (
  r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]*"
  r"(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]*){0,3}"
)
NUMBER_WORD = r"zero|one|two|three|four|five|six|seven|eight|nine|oh|o"
NAME_PARTICLES = r"van|von|der|den|de|del|da|la|le|di|du|dos|das"
FULL_NAME = rf"{NAME_TOKEN}(?:\s+(?:(?:{NAME_PARTICLES})\s+)*{NAME_TOKEN}){{1,3}}"
NAME_CUES = (
  r"DOB|MRN|on|has|with|presents|asks?|needs|due|from|is|came|called|wants|"
  r"says|lives|here|peri-menopausal"
)
PARENTHETICAL_NAME_EXCLUSIONS = (
  r"Tylenol|Acetaminophen|Ibuprofen|Motrin|Advil|Tums|Pentacel|Prevnar|"
  r"Rotavirus|Dupixent|Magnesium|Vitamin|DTaP|IPV|Hib|HepB|PCV|MMRV"
)
CAREGIVER_SUBJECT_TERMS = r"Mom|Mother|Dad|Father|Parent|Caregiver|Guardian|Caller|MOC|FOC"
CAREGIVER_REPORT_VERBS = (
  r"reports?|reported|says|said|states?|stated|notes?|noted|mentions?|mentioned|"
  r"observes?|observed"
)
PATIENT_NAME_FOLLOWERS = (
  r"had|has|was|is|reported|reports|improved|worse|worsened|needs|started|"
  r"stopped|takes|will|should|could|presented|presents|came|comes|reports|at"
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
    rf"\b(?i:La\s+(?:abuela|abuelo|t[ií]a|t[ií]o|mam[aá]|pap[aá]))"
    rf"(?:\s+{NAME_TOKEN})?\s+(?i:(?:dice|reporta|cuenta|menciona))"
    rf"\s+(?i:que\s+)?({NAME_TOKEN})\b",
  ),
  re.compile(
    rf"\b(?i:(?:{CAREGIVER_SUBJECT_TERMS}))(?:\s+{NAME_TOKEN})?\s+"
    rf"(?i:(?:{CAREGIVER_REPORT_VERBS}))\s+(?i:that\s+)?({NAME_TOKEN})"
    rf"(?=(?:'s)?\s+(?i:{PATIENT_NAME_FOLLOWERS})\b)",
  ),
  re.compile(
    rf"\b(?i:per)\s+(?i:(?:{CAREGIVER_SUBJECT_TERMS}))(?:\s+{NAME_TOKEN})?,\s+({NAME_TOKEN})"
    rf"(?=(?:'s)?\s+(?i:{PATIENT_NAME_FOLLOWERS})\b)",
  ),
  re.compile(
    rf"\b(?i:per)\s+(?i:(?:{CAREGIVER_SUBJECT_TERMS}))(?:\s+{NAME_TOKEN})?,\s+({NAME_TOKEN})"
    rf"(?=\s+and\s+(?i:sibling)\s+{NAME_TOKEN}\b)",
  ),
  re.compile(
    rf"\b(?i:per)\s+(?i:(?:{CAREGIVER_SUBJECT_TERMS}))(?:\s+{NAME_TOKEN})?,\s+{NAME_TOKEN}"
    rf"\s+and\s+(?i:sibling)\s+({NAME_TOKEN})\b",
  ),
  re.compile(
    rf"\b(?i:(?:La\s+mam[aá]|El\s+pap[aá]|Mi\s+hij[oa]|Su\s+hij[oa]|El\s+paciente|"
    rf"La\s+paciente))\s+(?:de\s+)?({NAME_TOKEN})\b",
  ),
  re.compile(
    rf"^({NAME_TOKEN})(?=,\s+(?i:per)\s+(?i:(?:{CAREGIVER_SUBJECT_TERMS}))\b)"
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
    r"\badmin(?:istrator)?\s+override\b[^.?!]*(?:[.?!]|$)",
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
  ("contextual_identifier", re.compile(r"\bonly\s+(?:[A-Za-z0-9+-]+\s+)?patient\b", re.IGNORECASE)),
  ("identifier", re.compile(r"\b[A-F0-9]{2}(?::[A-F0-9]{2}){5}\b", re.IGNORECASE)),
  ("identifier", re.compile(r"\b(?:[A-F0-9]{1,4}:){2,7}[A-F0-9]{0,4}\b", re.IGNORECASE)),
  ("identifier", re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
  )),
  ("identifier", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
  ("identifier", re.compile(
    r"\b(?:accession|claim|visit|specimen(?:\s+barcode)?|voiceprint\s+ID|passport|"
    r"military\s+ID|trial\s+ID|court\s+order|workstation|trace\s+ID|portal\s+token|"
    r"vaccine\s+inventory\s+lot|smartwatch\s+serial|device\s+serial|photo\s+file|"
    r"uploaded\s+file|QR\s+payload|certificate\s+number)\s*[:#-]?\s*"
    r"([A-Za-z0-9_=./|:%+-]{4,})",
    re.IGNORECASE,
  )),
  ("identifier", re.compile(
    r"\b(?:group|routing|extension|ext)\s*[:#-]?\s*([A-Z0-9 -]{3,})\b",
    re.IGNORECASE,
  )),
  ("identifier", re.compile(r"\b(?:GRP|SP|VP|SN|MIL|CERT|WATCH|WS)-[A-Z0-9-]{3,}\b", re.IGNORECASE)),
  ("identifier", re.compile(r"\bNCT-\d{8}\b", re.IGNORECASE)),
  ("identifier", re.compile(r"\b(?:AB|LP)\s*\d{3,}\s*\d{3,}\b", re.IGNORECASE)),
  ("identifier", re.compile(r"^(AB\d{6,})(?=:)")),
  ("identifier", re.compile(r"\bLP\d{6,}\b", re.IGNORECASE)),
  ("identifier", re.compile(r"\b[A-Za-z0-9_+-]+\.(?:jpg|jpeg|png|gif|pdf)\b", re.IGNORECASE)),
  ("identifier", re.compile(r"@[A-Za-z0-9_.-]+\b")),
  ("mrn", re.compile(r"\bMR\s*#\s*[A-Z0-9][A-Z0-9-]{3,}\b", re.IGNORECASE)),
  ("address", re.compile(
    rf"\b\d{{1,6}}\s+(?:[A-Za-z0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?",
    re.IGNORECASE,
  )),
  ("address", re.compile(
    rf"\b\d{{1,6}}\s+(?:[A-Za-zÀ-ÖØ-öø-ÿ0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?",
    re.IGNORECASE,
  )),
  ("address", re.compile(
    r"(?<!\w)(?:(?:Apt|Apartment|Unit|Suite|Ste)\.?\s+[A-Z0-9-]+|#\s*[A-Z0-9-]+)\b",
    re.IGNORECASE,
  )),
  ("location", re.compile(r"\b(?:bed|room|unit|floor|stop)\s+[A-Z0-9-]+\b", re.IGNORECASE)),
  ("location", re.compile(r"\b\d+(?:st|nd|rd|th)\s+floor\s+[A-Za-z0-9-]+\b", re.IGNORECASE)),
  ("location", re.compile(
    rf"\bbus\s+route\s+\d+\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}\s+stop\s+\d+\b",
    re.IGNORECASE,
  )),
  ("location", re.compile(r"\b(?:bus\s+route)\s+\d+\b", re.IGNORECASE)),
  ("location", re.compile(r"\bRoom\s+[A-Z0-9-]+\b", re.IGNORECASE)),
  ("location", re.compile(
    rf"\b(?i:(?:lives?|resides|located)\s+(?:at|in))\s+"
    rf"\d{{1,6}}\s+(?:[A-Za-z0-9'.-]+\s+){{0,5}}(?:{STREET_TYPES})\b\.?,\s*"
    rf"({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})\b",
  )),
  ("location", re.compile(rf"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){{0,2}},\s*(?:{US_STATE_ABBR})\b")),
  ("location", re.compile(rf"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?,\s*(?:{US_STATE_ABBR})\s+\d{{5}}(?:-\d{{4}})?\b")),
  ("location", re.compile(rf"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:{US_STATE_ABBR})\s+\d{{5}}(?:-\d{{4}})?\b")),
  ("location", re.compile(rf"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:{US_STATE_ABBR})\b")),
  ("location", re.compile(
    rf"\b(?i:(?:Going|travel(?:ing)?|travelling)\s+to)\s+"
    rf"((?!Camp\b){NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})\b",
  )),
  ("location", re.compile(
    rf"\b(?i:(?:from|near|in|at))\s+({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})"
    r"(?=\s*(?:[-,.;:)]|$))",
  )),
  ("zip", re.compile(r"\b(?:ZIP|zip code)\s*[:#]?\s*(\d{5}(?:-\d{4})?)\b", re.IGNORECASE)),
  ("zip", re.compile(r"\b\d{5}-\d{4}\b")),
  ("zip", re.compile(
    r"\b(?:lives?|resides)\s+(?:in|near|around)\s+(\d{5})(?:-\d{4})?"
    r"(?=\s+(?:area|zip|region|neighbou?rhood)\b|[,.;]|$)",
    re.IGNORECASE,
  )),
  ("zip", re.compile(
    r"\b(?:from|near|in)\s+(\d{5})(?:-\d{4})?"
    r"(?=\s+(?:area|zip|region|neighbou?rhood)\b|[,.;]|$)",
    re.IGNORECASE,
  )),
  ("zip", re.compile(
    r"\b(?:from|near|in|around)\s+(\d{5})(?:-\d{4})?"
    r"(?=\s+(?:with|who|has|and|for|asking|area|zip|region|neighbou?rhood)\b|[,.;]|$)",
    re.IGNORECASE,
  )),
  ("zip", re.compile(r"\b(\d{5})(?:-\d{4})?(?=\s+area\b)", re.IGNORECASE)),
  ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
  ("email", re.compile(
    r"\b([A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+"
    r"(?:\s+(?:dot|underscore|under\s+score|dash|hyphen)\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+){1,10}"
    r"\s+at\s+[A-Za-z0-9]+(?:\s+dot\s+[A-Za-z]{2,})+)\b",
    re.IGNORECASE,
  )),
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
  ("phone", re.compile(r"\+\d{1,3}(?:[\s().-]?\d){6,14}\b")),
  ("phone", re.compile(r"\b((?:\d\s+){9}\d)\b")),
  ("phone", re.compile(
    rf"\b((?:(?:{NUMBER_WORD})\s+){{9}}(?:{NUMBER_WORD}))\b",
    re.IGNORECASE,
  )),
  ("phone", re.compile(
    rf"\b((?:(?:{NUMBER_WORD})[-\s]+){{9}}(?:{NUMBER_WORD}))\b",
    re.IGNORECASE,
  )),
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
    r"\b(?:chart|account|acct|policy|member|subscriber|insurance policy)\s*"
    r"(?:number|no\.?|id|#)?\s*[:#-]?\s*([A-Z]{1,6}\s+\d{4,})\b",
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
  ("mrn", re.compile(r"\b(?:MRN|MR\s*#|MR#|medical record(?: number)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,})\b", re.IGNORECASE)),
  ("mrn", re.compile(r"\b[A-Z]{1,5}-\d{3,8}(?:-\d{3,8})?\b")),
  ("identifier", re.compile(r"\b[A-Z]{2,6}-\d{4,}(?:-[A-Z0-9]+)?\b")),
  ("ip_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
  ("url", re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/\S+", re.IGNORECASE)),
  ("url", re.compile(r"\b(?:https?://|mychart\.)\S+\b", re.IGNORECASE)),
  ("url", re.compile(
    r"\b(?:portal|patient|ehr|emr)\.(?:local|test|example|invalid|internal)(?:/\S*)?\b",
    re.IGNORECASE,
  )),
  ("pharmacy", re.compile(
    rf"\b(?:Walgreens|CVS|Rite Aid|Walmart Pharmacy|Costco Pharmacy|Kroger Pharmacy)"
    rf"\s+(?:on|at|in)\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}"
    rf"(?:\s+in\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})?\b",
    re.IGNORECASE,
  )),
  ("pharmacy", re.compile(
    rf"\b(?:pharmacy|retail\s+pharmacy)\s+(?:is\s+)?(?:a\s+)?(?:retail\s+)?pharmacy"
    rf"\s+(?:on|at|in)\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}"
    rf"(?:\s+in\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})?\b",
    re.IGNORECASE,
  )),
  ("school", re.compile(
    rf"\b(?:{NAME_TOKEN}\s+){{1,4}}(?:(?:Elementary|Middle|High)(?:\s+School)?|School|Academy)\b",
  )),
  ("camp", re.compile(rf"\bCamp\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}\b")),
  ("practice", re.compile(
    r"\b(?:Lakes\s+Pediatrics|Children['’]s(?:\s+Hospital)?|Mayo\s+Clinic|Cleveland\s+Clinic|"
    r"[A-Z][A-Za-z'’.-]+\s+(?:Pediatrics|Clinic|Hospital|Family Medicine|Medical Group|"
    r"Health|Urgent Care|Rehab|Institute))\b",
    re.IGNORECASE,
  )),
  ("insurance", re.compile(
    r"\b(?:Blue\s+Cross|BCBS|Aetna|Cigna|UnitedHealth(?:care)?|Kaiser|Humana|"
    r"Anthem|Medicaid|Medicare|Tricare)\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b")),
  ("date", re.compile(r"\b\d{8}\b")),
  ("date", re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)?\b")),
  ("date", re.compile(r"\b\d{1,2}\s+\d{1,2}\s+\d{4}\b")),
  ("date", re.compile(
    r"\b(?:today|tomorrow|yesterday|next\s+month|last\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|month))\b",
    re.IGNORECASE,
  )),
  ("date", re.compile(r"\b(?:at|collected|seen)\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)\b", re.IGNORECASE)),
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
  ("age", re.compile(r"\b\d{1,3}-month-olds?\b", re.IGNORECASE)),
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
  ("name", re.compile(rf'"(?i:first)"\s*:\s*"({NAME_TOKEN})"')),
  ("name", re.compile(rf'"(?i:last)"\s*:\s*"({NAME_TOKEN})"')),
  ("name", re.compile(rf"\b(?i:PATIENT)\s*:\s*({NAME_TOKEN}),\s*{NAME_TOKEN}\b")),
  ("name", re.compile(rf"\b(?i:PATIENT)\s*:\s*{NAME_TOKEN},\s*({NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b[A-Za-z][A-Za-z/ &-]{{2,80}}\s+\("
    rf"((?!(?:{PARENTHETICAL_NAME_EXCLUSIONS})\b){NAME_TOKEN})"
    rf"(?:,\s*\d{{1,2}}(?:st|nd|rd|th)\s+grade)?\)(?=\s*:)"
  )),
  ("name", re.compile(
    rf"\("
    rf"((?!(?:{PARENTHETICAL_NAME_EXCLUSIONS})\b){NAME_TOKEN})"
    rf",\s*\d{{1,2}}(?:st|nd|rd|th)\s+grade\)"
  )),
  ("name", re.compile(rf"\|\|({NAME_TOKEN}\^{NAME_TOKEN})\|\|")),
  ("name", re.compile(rf"\bPAT=({NAME_TOKEN}-{NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:signature\s+block|signed\s+by|electronically\s+signed\s+by))\s*:\s*"
    rf"({FULL_NAME})(?=,\s*(?:MD|DO|NP|PA|PA-C|RN|LPN|LVN|PharmD)\b)"
  )),
  ("name", re.compile(
    rf"^[A-Z0-9]{{4,}}:\s+({NAME_TOKEN})"
    rf"(?=\s+(?i:{PATIENT_NAME_FOLLOWERS})\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:legal\s+name)\s*[:#-]?\s*({FULL_NAME}|{NAME_TOKEN}|{LABEL_NAME_VALUE})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:preferred\s+name|patient\s+name|name|alias))\s*[:#-]\s*({FULL_NAME}|{NAME_TOKEN}|{LABEL_NAME_VALUE})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:patient\s+name|nickname|alias))\s+({FULL_NAME}|{NAME_TOKEN})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:patient)\s*:\s*({FULL_NAME})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:chart\s+says)\s+({FULL_NAME})(?=,\s*(?i:(?:DOB|date of birth|D\.O\.B\.?))\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:child|patient))'?s?\s+name\s+is\s+({FULL_NAME}|{NAME_TOKEN}|{LABEL_NAME_VALUE})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:patient\s+named)\s+({FULL_NAME}|{NAME_TOKEN})"
    rf"(?=\s+(?i:{PATIENT_NAME_FOLLOWERS})\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:patient\s+named)\s+({FULL_NAME})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:patient\s+goes\s+by)\s+({FULL_NAME}|{NAME_TOKEN}|{LABEL_NAME_VALUE})\b"
  )),
  ("name", re.compile(
    rf"\b(?i:caller)\s+({NAME_TOKEN})(?=\s+at\b)"
  )),
  ("name", re.compile(
    rf"\b(?i:(?:matched\s+caller|parent))\s+({NAME_TOKEN})\b",
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
  ("name", re.compile(
    rf"\b(?i:(?:for|belongs\s+to|attached\s+to|linked\s+to|under|identifies|"
    rf"posted\s+patient|for\s+patient|for\s+pt|on|with))\s+({FULL_NAME})\b"
    rf"(?=\s*(?:[.,;:]|$|\s+(?:has|with|asks?|adult|child|infant|new|collected|at|scanned|from|shows|returned)))",
  )),
  ("name", re.compile(
    rf"\b(?i:(?:with|for))\s+({FULL_NAME})'s\b",
  )),
  ("name", re.compile(
    rf"\b(?i:for)\s+({NAME_TOKEN})"
    rf"(?=\s+(?i:(?:before|after|about|regarding|with|because|due|needs|started|stopped|has|had|is|was))\b)",
  )),
  ("name", re.compile(
    rf"\b(?i:(?:from|to|saw))\s+({FULL_NAME}|{NAME_TOKEN}\s+[A-Z])\b"
    rf"(?=\s*(?:[.,;:]|$|\s+(?:at|has|shows|says|asks?)))",
  )),
  ("name", re.compile(rf"\b(?i:(?:{RELATION_TERMS}))\s+({NAME_TOKEN})\b")),
  ("name", re.compile(rf"\b(?i:(?:{RELATION_TERMS}))\s+\(({NAME_TOKEN})\)(?=\W|$)")),
  ("name", re.compile(rf"\b(?i:little)\s+({NAME_TOKEN})\b")),
  ("name", re.compile(rf"\b(?i:(?:today|same-day))\s+is\s+({NAME_TOKEN})\b")),
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
    rf"^(?!(?:{RELATION_TERMS}|Caller|Callback|Fax|Phone|Email|Chart|Account|Policy|Visit|Encounter)\b)({NAME_TOKEN})"
    r"(?=\s+(?:has|presents|needs|asks|is|was|reports|states)\b)"
  )),
  ("name", re.compile(rf"\b(?:calls?\s+(?:him|her|them)|known\s+as|nicknamed)\s+({NAME_TOKEN})\b")),
  ("name", re.compile(
    rf"\b(?i:(?:Pt|Patient|Family of|chart for|for patient|for pt))\s+({FULL_NAME})"
    rf"(?=\s*(?:,|\(|\b(?i:(?:{NAME_CUES}))\b|\d{{1,3}}\s*(?:M|F)\b|\d{{1,3}}\s*(?:{EXPLICIT_AGE_UNITS})\b))",
  )),
  ("name", re.compile(
    rf"\b(?i:re)\s*:\s*({NAME_TOKEN})(?=\s*[.;:,-]\s*(?i:(?:he|she|they|pt|patient))\b)"
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
  ("possible city/state location remains", re.compile(
    rf"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){{0,2}},\s*(?:{US_STATE_ABBR})\b"
  )),
  ("possible practice or facility remains", re.compile(r"\b[A-Z][A-Za-z'’.-]+\s+(?:Pediatrics|Clinic|Hospital|Medical Group|Health|Urgent Care|Rehab|Institute)\b")),
)

RESIDUAL_MEDIUM_RISK: tuple[tuple[str, re.Pattern[str]], ...] = (
  ("possible exact date remains", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
  ("possible direct name remains", re.compile(r"\b(?:Mr|Mrs|Ms|Miss)\.?\s+[A-Z][a-z]{2,}\b")),
  ("possible patient name remains", re.compile(
    rf"\b(?i:(?:Pt|Patient|Family of|chart for|for patient|for pt))\s+{FULL_NAME}\b",
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
  (re.compile(
    r"\b(?:Mom|Mother|Dad|Father|Parent|MOC|FOC)(?:\s+\[NAME\])?\s+"
    r"(?:reports?|says|states?|notes?|mentions?|observes?)\s+(?:that\s+)?\[NAME\]",
    re.IGNORECASE,
  ), "parent reports patient"),
  (re.compile(
    r"\bPer\s+(?:mom|mother|dad|father|parent|MOC|FOC)(?:\s+\[NAME\])?,\s+\[NAME\]",
    re.IGNORECASE,
  ), "parent reports patient"),
  (re.compile(
    r"\b\[NAME\],\s+per\s+(?:mom|mother|dad|father|parent|MOC|FOC)\b",
    re.IGNORECASE,
  ), "patient"),
  (re.compile(r"\b(?:Mom|Mother|Dad|Father)\s+\[NAME\]", re.IGNORECASE), "parent"),
  (re.compile(r"\b(?:MOC|FOC)\s+\[NAME\]", re.IGNORECASE), "parent"),
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
  "%m %d %Y",
  "%m %d %y",
  "%Y-%m-%d",
  "%Y/%m/%d",
  "%B %d, %Y",
  "%b %d, %Y",
  "%B %d %Y",
  "%b %d %Y",
  "%d %B %Y",
  "%d %b %Y",
)


def _collect_spans(text: str, extra_spans: Iterable[Span] = ()) -> list[Span]:
  spans: list[Span] = []
  for category, pattern in PATTERNS:
    for match in pattern.finditer(text):
      if match.lastindex:
        start, end = match.span(match.lastindex)
      else:
        start, end = match.span(0)
      if start != end:
        spans.append(Span(category=category, start=start, end=end))
  spans.extend(extra_spans)
  spans.extend(_propagated_patient_name_spans(text))
  return _select_non_overlapping(spans)


def _engine_extra_spans(
  text: str,
  *,
  requested_engine: str,
  span_detector: SpanDetector | None,
) -> tuple[str, str, list[Span]]:
  if requested_engine not in SUPPORTED_ENGINES:
    raise ValueError(
      f"Unsupported decon engine '{requested_engine}'. "
      f"Supported engines: {', '.join(sorted(SUPPORTED_ENGINES))}."
    )
  if requested_engine == LOCAL_RULES_ENGINE:
    return LOCAL_RULES_ENGINE, "", []
  if span_detector is not None:
    return OPENMED_ENGINE, "", _complete_bare_name_span(text, span_detector(text))

  try:
    from .model_setup import get_model_status
    status = get_model_status()
    if not status.ner_model_ready:
      reason = "OpenMed model is not installed; used local-rules engine."
      return LOCAL_RULES_ENGINE, reason if requested_engine == OPENMED_ENGINE else "", []

    from .openmed_ner import OpenMedUnavailable, get_openmed_span_detector
    try:
      detector = get_openmed_span_detector(status.model_id, str(status.model_dir))
      return OPENMED_ENGINE, "", _complete_bare_name_span(text, detector(text))
    except OpenMedUnavailable as exc:
      reason = f"OpenMed unavailable: {exc}; used local-rules engine."
      return LOCAL_RULES_ENGINE, reason if requested_engine == OPENMED_ENGINE else "", []
  except Exception as exc:
    reason = f"OpenMed setup failed: {exc}; used local-rules engine."
    return LOCAL_RULES_ENGINE, reason if requested_engine == OPENMED_ENGINE else "", []


def _complete_bare_name_span(text: str, detected_spans: Iterable[Span]) -> list[Span]:
  """Complete a two-token name when OpenMed recognizes only one token.

  A bare first-and-last-name paste has no clinical value to preserve. Restricting
  this expansion to the entire two-token input avoids guessing at adjacent words
  inside a note while ensuring a partial model span cannot approve a leaked
  surname.
  """
  spans = list(detected_spans)
  match = BARE_TWO_TOKEN_NAME.fullmatch(text)
  if match is None:
    return spans

  phrase_start, phrase_end = match.span(1)
  has_name_detection = any(
    span.category == "name"
    and span.start < phrase_end
    and span.end > phrase_start
    for span in spans
  )
  if not has_name_detection:
    return spans

  return [span for span in spans if span.category != "name"] + [
    Span(category="name", start=phrase_start, end=phrase_end),
  ]


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


def _span_metadata(spans: list[Span]) -> list[dict[str, int | str]]:
  return [
    {
      "category": span.category,
      "start": span.start,
      "end": span.end,
      "confidence": "review" if span.category in REVIEW_SPAN_CATEGORIES else "confident",
    }
    for span in sorted(spans, key=lambda item: item.start)
  ]


def _replacement_for_span(text: str, span: Span, reference_date: date) -> str:
  raw = text[span.start:span.end]
  if span.category == "prompt_injection":
    return ""
  if span.category == "contextual_identifier":
    disease_marker = re.search(r"\bonly\s+([A-Z]{2,8})\s+patient\b", raw, re.IGNORECASE)
    if disease_marker:
      return f"Rare {disease_marker.group(1).upper()} case"
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
  safe = _normalize_hl7_context(safe)
  safe = _strip_ehr_wrapper_noise(safe)
  safe = re.sub(r"\[NAME\]'s\b", "patient's", safe)
  safe = re.sub(r"\bBoth\s+\[NAME\]\s+and\s+(?:his|her|their)\s+mother\b", "Both patient and mother", safe, flags=re.IGNORECASE)
  safe = re.sub(
    rf"\b(?:{DOB_LABEL})\s*[:#.-]?\s*"
    rf"(?:is\s+)?"
    rf"(?=(?:{SAFE_AGE_PATTERN})(?:\s+(?:male|female))?\b)",
    "",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(
    r"\b((?:older\s+)?adult(?:\s+age)?\s+(?:18-44|45-64|65-74|75-89|90\s+or\s+older))\s+adult\b",
    r"\1",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(r"\b(?:MRN|MR#)\s+\[MRN\]", "[MRN]", safe, flags=re.IGNORECASE)
  safe = re.sub(r"\bSSN\s+\[SSN\]", "[SSN]", safe, flags=re.IGNORECASE)
  for pattern, replacement in RELATION_REPLACEMENTS:
    safe = pattern.sub(replacement, safe)
  safe = re.sub(r"\s+([,.;:])", r"\1", safe)
  return safe


def _normalize_hl7_context(text: str) -> str:
  if not re.search(r"(?m)^(?:MSH|PID|OBX)\|", text):
    return text

  sex = None
  lab_summaries: list[str] = []
  non_hl7_lines: list[str] = []
  for line in text.splitlines():
    stripped = line.strip()
    if not stripped:
      continue
    segment = stripped.split("|", 1)[0]
    if segment == "PID":
      fields = stripped.split("|")
      if len(fields) > 8:
        sex_code = fields[8].strip().upper()
        if sex_code == "F":
          sex = "female"
        elif sex_code == "M":
          sex = "male"
      continue
    if segment == "OBX":
      fields = stripped.split("|")
      if len(fields) > 5:
        label = fields[3].split("^", 1)[0].strip()
        value = fields[5].strip()
        if label and value and re.fullmatch(LAB_TERMS, label, flags=re.IGNORECASE):
          lab_summaries.append(_generalize_clinical_value(f"{label} {value}"))
      continue
    if segment in {"MSH", "OBR", "ORC", "PV1", "DG1"}:
      continue
    non_hl7_lines.append(stripped)

  clinical_parts = []
  if sex:
    clinical_parts.append(f"{sex} patient")
  clinical_parts.extend(summary for summary in lab_summaries if summary not in clinical_parts)
  clinical_parts.extend(non_hl7_lines)
  if not clinical_parts:
    return text
  return ". ".join(clinical_parts)


def _strip_ehr_wrapper_noise(text: str) -> str:
  safe = text
  safe = re.sub(
    r"\b(?:ELATION|EHR|EMR)\s+(?:NOTE|SUMMARY|EXPORT|MESSAGE)\b\s*:?",
    " ",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(r"\bNOTE\s+CONTENT\b\s*:?", " ", safe, flags=re.IGNORECASE)
  safe = re.sub(r"\b(?:Patient|Pt)\s*:\s*\[NAME\]\s*:?", " ", safe, flags=re.IGNORECASE)
  safe = re.sub(
    r"\b(?:MRN|MR#|medical record(?: number)?)\s*:\s*\[(?:MRN|IDENTIFIER)\]\s*",
    " ",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(
    r"\b(?:Serviced at|Service date|Encounter date|Visit date)\s*:\s*\[DATE\]\s*",
    " ",
    safe,
    flags=re.IGNORECASE,
  )
  safe = re.sub(
    r"\bSex\s*:\s*(Male|Female)\b",
    lambda match: match.group(1).lower(),
    safe,
    flags=re.IGNORECASE,
  )
  return safe


def _normalize_age(raw: str) -> str:
  hyphen_month_match = re.search(
    r"\b(?P<amount>\d{1,3})-month-olds?\b",
    raw,
    flags=re.IGNORECASE,
  )
  if hyphen_month_match:
    amount = int(hyphen_month_match.group("amount"))
    return _age_band_from_months(amount)
  hyphen_year_match = re.search(
    r"\b(?P<amount>\d{1,3})-year-olds?\b",
    raw,
    flags=re.IGNORECASE,
  )
  if hyphen_year_match:
    amount = int(hyphen_year_match.group("amount"))
    return _age_band_from_years(amount)
  compact_match = re.search(
    r"\b(?P<amount>\d{1,3})\s*(?P<sex>M|F)\b",
    raw,
    flags=re.IGNORECASE,
  )
  if compact_match:
    amount = int(compact_match.group("amount"))
    sex = "male" if compact_match.group("sex").lower() == "m" else "female"
    return _age_band_from_years(amount, sex=sex)
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
    return _age_band_from_months(amount)
  return _age_band_from_years(amount)


def _age_band_from_years(years: int, *, sex: str | None = None) -> str:
  if years >= 90:
    phrase = "adult age 90 or older"
  elif years >= 75:
    phrase = "older adult 75-89"
  elif years >= 65:
    phrase = "older adult 65-74"
  elif years >= 45:
    phrase = "adult 45-64"
  elif years >= 18:
    phrase = "adult 18-44"
  elif years >= 13:
    phrase = "adolescent"
  elif years >= 11:
    phrase = "early adolescent"
  elif years >= 5:
    phrase = "school-age child"
  elif years >= 2:
    phrase = "preschool child"
  elif years == 1:
    phrase = "toddler 12-23 months"
  else:
    phrase = "newborn"
  return f"{phrase} {sex}" if sex else phrase


def _age_band_from_months(months: int) -> str:
  if months <= 0:
    return "newborn"
  if months < 6:
    return "infant under 6 months"
  if months < 12:
    return "infant 6-11 months"
  if months < 24:
    return "toddler 12-23 months"
  return _age_band_from_years(months // 12)


def _parse_date(raw: str) -> date | None:
  normalized = re.sub(r"(\d{1,2})(?:st|nd|rd|th)", r"\1", raw, flags=re.IGNORECASE)
  normalized = re.sub(r"\b([A-Za-z]{3})\.", r"\1", normalized)
  normalized = re.sub(r"\b(?:März|Maerz|Marz)\b", "March", normalized, flags=re.IGNORECASE)
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
  if years >= 2:
    return _age_band_from_years(years)
  months = (reference_date.year - dob.year) * 12 + reference_date.month - dob.month
  if reference_date.day < dob.day:
    months -= 1
  return _age_band_from_months(months)


def _derive_age_for_date(text: str, span: Span, reference_date: date) -> str | None:
  context = text[max(0, span.start - 24):span.start].lower()
  if not re.search(rf"\b(?:{DOB_LABEL})\b", context, re.IGNORECASE):
    return None
  parsed = _parse_date(text[span.start:span.end])
  if parsed is None:
    return None
  return _age_from_dob(parsed, reference_date)


def _extract_safe_age(source: str, reference_date: date) -> str | None:
  safe_age_match = re.search(
    rf"\b(?:{SAFE_AGE_PATTERN})(?:\s+(?:male|female))?\b",
    source,
    flags=re.IGNORECASE,
  )
  if safe_age_match:
    return safe_age_match.group(0)
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
    rf"(?:is\s+)?"
    rf"(\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|\d{{1,2}}\s+\d{{1,2}}\s+\d{{4}}|"
    rf"\d{{4}}[/-]\d{{1,2}}[/-]\d{{1,2}}|"
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
  return bool(re.search(r"\b(?:newborn|infant|toddler|child|adolescent)\b", age, re.IGNORECASE))


def _generalize_date(raw: str) -> str:
  lowered = raw.lower()
  if lowered == "today":
    return "same-day"
  if lowered == "tomorrow":
    return "next day"
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
  query = re.sub(r"^(?:is|was|are|were)\s*(?:[;:,.]\s*)?", "", query, flags=re.IGNORECASE)
  if 0 < len(re.findall(r"[A-Za-z][A-Za-z0-9+-]*", query)) < 4:
    query = f"{query} clinical guidance".strip()
  return query or "de-identified clinical question"


def _age_query_hint(age: str | None, *, lower_source: str, topic: str) -> str:
  if not age:
    return ""
  base = re.sub(r"\s+(?:male|female)\b", "", age, flags=re.IGNORECASE).strip()
  if topic == "hpv" and base == "early adolescent":
    return "early adolescent in HPV/Tdap vaccine range"
  if topic == "vaccine" and base in {"infant 6-11 months", "toddler 12-23 months"}:
    return f"{base} vaccine schedule range"
  if "screening" in lower_source and re.search(r"\b(?:adult 45-64|older adult 65-74)\b", base):
    return "adult in preventive screening age range"
  return base


def _safe_query_from_text(source: str, safe_context: str, reference_date: date) -> str:
  lower_source = source.lower()
  safe_age = _extract_safe_age(source, reference_date) or _extract_safe_age(safe_context, reference_date)
  vaccine_age_hint = _age_query_hint(safe_age, lower_source=lower_source, topic="vaccine")
  hpv_age_hint = _age_query_hint(safe_age, lower_source=lower_source, topic="hpv")
  pediatric_label = "" if safe_age else "pediatric "
  if re.search(
    r"\b(?:under-immunized|under immunized|catch-up|siblings?|separate shots|adhd)\b",
    lower_source,
  ):
    return _safe_query_from_context(safe_context)
  if re.search(
    r"\b(?:travel|typhoid|malaria|prophylaxis|doxycycline|reaction|rash|fever|"
    r"counseling)\b",
    lower_source,
  ):
    return _safe_query_from_context(safe_context)
  if re.search(r"\b(?:hpv|human papillomavirus)\b", lower_source):
    age_prefix = f"{hpv_age_hint} " if hpv_age_hint else ""
    return f"{age_prefix}{pediatric_label}HPV vaccine schedule current guidelines".strip()
  if re.search(r"\b(?:vaccine|vaccines|vaccination|immunization|shots)\b", lower_source):
    age_prefix = f"{vaccine_age_hint} " if vaccine_age_hint else ""
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
  engine: str = AUTO_ENGINE,
  span_detector: SpanDetector | None = None,
) -> LocalDeconResult:
  """Run local rule-based decontextualization and render destination handoff data."""
  source = text.strip()
  ref_date = reference_date or date.today()
  actual_engine, engine_fallback_reason, extra_spans = _engine_extra_spans(
    source,
    requested_engine=engine,
    span_detector=span_detector,
  )
  spans = _collect_spans(source, extra_spans)
  safe_context, removed_categories = _apply_spans(source, spans, ref_date)
  safe_query = _safe_query_from_text(source, safe_context, ref_date)
  risk_level, risk_reasons = _risk(safe_context)
  if engine == OPENMED_ENGINE and engine_fallback_reason:
    risk_level = "high"
    risk_reasons = [*risk_reasons, engine_fallback_reason]
  destination_prompt = render_prompt(destination, safe_context=safe_context, safe_query=safe_query)
  handoff = build_handoff(destination, destination_prompt)
  return LocalDeconResult(
    original_length=len(source),
    destination=destination,
    safe_context=safe_context,
    safe_query=safe_query,
    destination_prompt=destination_prompt,
    removed_categories=removed_categories,
    removed_spans=_span_metadata(spans),
    risk_level=risk_level,
    risk_reasons=risk_reasons,
    copy_allowed=risk_level != "high",
    open_url=handoff.open_url,
    action_label=handoff.action_label,
    engine=actual_engine,
    engine_requested=engine,
    engine_fallback_reason=engine_fallback_reason,
  )

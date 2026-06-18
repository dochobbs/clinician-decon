# Decon Vs De-ID Explainer

## Short Version

De-identification and decontextualization solve different problems.

De-identification asks:

> Can this document or dataset be shared with identifiers removed?

Decontextualization asks:

> Can this clinician safely ask a useful question without sending raw PHI?

That difference matters. A de-ID system often tries to remove, mask, or transform identifiers
inside a note. A decon system is more task-aware: it removes direct identifiers and risky context,
then preserves the minimum clinical facts needed for the next question.

Clinician Decon is not a legal de-identification certification tool. It is a local PHI-minimizing
prompt builder for clinicians who need a safer, clinically useful handoff to an external AI,
search, or reference workflow.

## Why Decon Is Not Just "More Redaction"

The goal is not to make the text as empty as possible. The goal is to make the text safe enough to
review and useful enough to answer.

That means decon has three jobs:

1. Remove direct identifiers: names, MRNs, birth dates, phones, emails, addresses, facilities, room
   numbers, provider names, and similar patient-specific handles.
2. Reduce re-identification context: exact dates, very specific ages, rare "only patient" clues,
   local workflow details, schools, camps, pharmacies, and unusual location context.
3. Preserve clinical signal: diagnoses, symptoms, medication names, doses, timing, severity,
   relationship roles, pregnancy status, weights for dosing, and labs when they drive the answer.

A traditional de-ID output can be safer as a document release but worse as a clinical prompt. A
decon output can keep clinically important data that a broad de-ID pass might redact, because
without that data the external tool cannot answer the clinician's actual question.

## The Practical Rule

Keep a fact when all three are true:

- It is needed to answer the clinical question.
- It is not a direct identifier by itself.
- It has been generalized when exactness is not clinically necessary.

Remove or generalize a fact when any of these are true:

- It directly identifies the patient, caregiver, clinician, facility, or local workflow.
- It narrows the patient too much through time, place, rare status, or "only patient" context.
- It is exact but the clinical question only needs a category or band.

## Side-By-Side Examples

These examples are synthetic and illustrative. Exact output can vary by destination profile and
risk level, but the policy difference is the important part.

### 1. Vaccine Question: Keep Age Band, Remove DOB

Input:

```text
Noah Rivera DOB 3/15/2013 MRN LP-2024-08432 needs catch-up vaccines before school starts Monday.
```

Traditional de-ID style:

```text
[NAME] DOB [DATE] MRN [ID] needs catch-up vaccines before school starts [DATE].
```

Decon style:

```text
[NAME] adolescent [MRN] needs catch-up vaccines before school starts [DATE].
```

Why data stays:

The exact date of birth is identifying and unnecessary. The age band is clinically essential
because vaccine recommendations depend on age.

What decon adds:

It does not just blank the DOB. It converts the DOB into the clinical signal the clinician actually
needed.

### 2. Weight-Based Dosing: Keep Exact Weight

Input:

```text
Maya Thompson is 28 kg and needs epinephrine autoinjector dose after peanut anaphylaxis.
```

Traditional de-ID style:

```text
[NAME] is [NUMBER] kg and needs epinephrine autoinjector dose after peanut anaphylaxis.
```

Decon style:

```text
[NAME] is 28 kg and needs epinephrine autoinjector dose after peanut anaphylaxis.
```

Why data stays:

Weight is not a direct identifier here, and the exact value changes the dose decision. Redacting it
would make the output safer-looking but less clinically useful.

What decon adds:

It keeps the clinically decisive numeric value while removing the person.

### 3. Medication Safety: Keep Condition And Drug, Remove Person

Input:

```text
Avery L has Gilbert syndrome, how much acetaminophen can they have?
```

Traditional de-ID style:

```text
[NAME] has [CONDITION], how much [MEDICATION] can they have?
```

Decon style:

```text
[NAME] has Gilbert syndrome, how much acetaminophen can they have?
```

Why data stays:

The diagnosis and medication are the whole clinical question. Removing them protects the shape of
the note but destroys the clinical task.

What decon adds:

It removes the patient reference and leaves the disease-drug relationship intact.

### 4. Eponym Collision: Remove Name, Preserve Diagnosis

Input:

```text
Referral for Addison Brooks. Addison disease on fludrocortisone, vomiting; stress-dose steroid?
```

Traditional de-ID style:

```text
Referral for [NAME]. [NAME] disease on fludrocortisone, vomiting; stress-dose steroid?
```

Decon style:

```text
Referral for [NAME]. Addison disease on fludrocortisone, vomiting; stress-dose steroid?
```

Why data stays:

`Addison Brooks` is a patient name. `Addison disease` is a diagnosis. A blunt de-ID tool can confuse
the two because the same token appears in both places.

What decon adds:

It protects the identifier without deleting the clinical eponym needed for the question.

### 5. Severe Labs: Remove Location, Keep Decision-Critical Values

Input:

```text
Only HLH patient in Room 712 today: ferritin 18000, platelets 22, fibrinogen 92.
Does this meet treatment criteria?
```

Traditional de-ID style:

```text
Only [CONDITION] patient in [LOCATION] [DATE]: ferritin [NUMBER], platelets [NUMBER],
fibrinogen [NUMBER]. Does this meet treatment criteria?
```

Decon style:

```text
Rare HLH case: ferritin 18000, platelets 22, fibrinogen 92.
Does this meet treatment criteria?
```

Why data stays:

The room and same-day context are re-identification risks. The lab values are central to severity
and criteria.

What decon adds:

It removes the local uniqueness trail while preserving the values that determine the medical
answer.

### 6. Pregnancy Medication: Keep Gestational Age, Remove Pharmacy

Input:

```text
Pregnant patient at 18 weeks asks if nitrofurantoin is okay for UTI; pharmacy is on Vernon.
```

Traditional de-ID style:

```text
Pregnant patient at [NUMBER] weeks asks if [MEDICATION] is okay for [CONDITION];
pharmacy is [LOCATION].
```

Decon style:

```text
Pregnant patient at 18 weeks asks if nitrofurantoin is okay for UTI; pharmacy is [LOCATION].
```

Why data stays:

Gestational age and medication name are needed for pregnancy medication safety. Pharmacy location
is not needed and can identify the patient through a local pickup pattern.

What decon adds:

It keeps the trimester-specific decision point and removes the local logistics.

### 7. Sibling Exposure: Keep Relationship Roles, Remove Household Identity

Input:

```text
Twin A has fever and vesicular rash; sibling in the same household has newborn exposure.
Family asks about isolation.
```

Traditional de-ID style:

```text
[RELATIVE] has fever and vesicular rash; [RELATIVE] in the same household has [AGE] exposure.
Family asks about isolation.
```

Decon style:

```text
Pediatric patient has fever and vesicular rash; sibling in same household has newborn exposure.
Family asks about isolation.
```

Why data stays:

Sibling and newborn exposure are not just demographics. They change infectious disease risk and
isolation advice.

What decon adds:

It preserves the household exposure structure without keeping names, dates, addresses, or local
context.

### 8. ADHD Medication Follow-Up: Keep Sequence, Remove Travel Date

Input:

```text
Jordan Ellis stopped methylphenidate 2 days ago because anxiety worsened. Parent asks whether
guanfacine 1 mg every morning is reasonable before camp July 12.
```

Traditional de-ID style:

```text
[NAME] stopped [MEDICATION] [DATE] because [SYMPTOM] worsened. [RELATIVE] asks whether
[MEDICATION] [DOSE] is reasonable before [EVENT] [DATE].
```

Decon style:

```text
Patient stopped methylphenidate 2 days ago because anxiety worsened. Parent asks whether
guanfacine 1 mg every morning is reasonable before camp [DATE].
```

Why data stays:

Medication sequence, side effect, relative timing, and dose are needed to assess the plan. The
patient name and exact camp date are not.

What decon adds:

It keeps the treatment narrative while stripping the identity and calendar details.

### 9. Weak Clinical Prompt: Safe Can Still Be Useless

Input:

```text
pt reports saw Dr. Thomas on 4/12/26
```

Traditional de-ID style:

```text
pt reports saw Dr. [NAME] on [DATE]
```

Decon style:

```text
pt reports saw Dr. [NAME] on [DATE]
```

Why this is different:

This output is safer, but it is not clinically useful. There is no question, symptom, medication,
diagnosis, or decision point.

What decon should do:

The app should make the clinician review the prompt and add a non-identifying clinical question
before using it externally.

## What Often Stays In Decon But Disappears In De-ID

| Data type | Why decon may keep it | Safer decon pattern |
| --- | --- | --- |
| Age signal | Needed for vaccine, dosing, risk, and guidelines | age band instead of DOB or exact age |
| Exact weight | Needed for weight-based dosing | keep weight when dosing depends on it |
| Medication dose | Needed to judge safety, titration, or interactions | keep drug and dose, remove pharmacy and dates |
| Severe labs | Needed for criteria and acuity | keep values when they drive triage |
| Gestational age | Needed for pregnancy medication guidance | keep weeks or trimester, remove dates and facility |
| Relationship role | Needed for history and exposure context | keep parent/sibling/newborn role, remove names |
| Clinical eponym | Needed for diagnosis | preserve `Addison disease`, redact `Addison Brooks` |
| Relative timing | Needed for medication onset or symptom course | keep `2 days ago`, remove exact calendar dates when risky |

## What Decon Removes Even If A De-ID Tool Might Miss It

Decon is often stricter about context that makes a patient findable:

- `only HLH patient on 7th floor today`
- `pharmacy on Vernon`
- `camp starts July 12`
- `saw Dr. Thomas on 4/12/26`
- `portal callback from 512-555-0147`
- `Room 712`, `Bed B`, `Unit 4`
- local school, camp, practice, facility, or workflow labels
- URLs, portal tokens, QR payloads, filenames, device IDs, and account handles

Those details may not look like classic name/MRN PHI in isolation, but they can identify a patient
when combined with clinical rarity, time, and place.

## How To Explain It To A Clinician

Use this framing:

> De-ID is for sharing a record. Decon is for asking a safer question.

Or:

> De-ID tries to remove identifiers from the note. Decon tries to keep the medical question alive
> while removing the patient.

Or:

> A de-ID note can be technically cleaner but clinically useless. A decon prompt should be reviewed,
> minimal, and still answerable.

## How To Explain It To A Reviewer

Use this framing:

> This tool does not certify that a document is de-identified. It locally minimizes PHI for a
> clinician-reviewed prompt handoff. Its safety target is "minimum necessary context for this
> specific question," not "release this whole chart note."

That distinction should stay visible in product copy, installer docs, and demos.

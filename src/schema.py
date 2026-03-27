"""
Full Q1–Q21 survey schema, OpenAI JSON-schema definition, and prompt template.
"""

# ---------------------------------------------------------------------------
# Valid option lists (exact text that can appear in each answer)
# ---------------------------------------------------------------------------

Q4_OPTIONS = [
    "Less than 1 year",
    "1-5 years",
    "6-10 years",
    "10-20 years",
    "More than 20 years",
]

Q5_SCALE = ["Very dissatisfied", "Dissatisfied", "Neutral", "Satisfied", "Very satisfied"]
Q5_ITEMS = [
    ("q5_peers", "Communication with peers (colleagues/those you work with)"),
    ("q5_supervisor", "Communication from/with your direct supervisor"),
    ("q5_shop", "Communication from your shop"),
    ("q5_leadership", "Communication from top-level SHA leadership"),
    ("q5_overall", "Overall satisfaction"),
]

Q6_SCALE = ["Very disagree", "Disagree", "Neutral", "Agree", "Very agree"]
Q6_ITEMS = [
    ("q6_available", "My direct supervisor is available when I need help"),
    ("q6_knows_problems", "My direct supervisor knows when I have problems at work"),
    ("q6_understands", "My supervisor understands my problems"),
    ("q6_potential", "My supervisor sees my potential"),
]

Q7_OPTIONS = ["Never", "Rare", "Sometimes", "Often", "Very often"]
Q8_OPTIONS = ["Never", "Rarely", "Sometimes", "Often", "Very often"]

Q9_OPTIONS = [
    "Training",
    "HR updates",
    "Safety messages",
    "License reminders",
    "Daily work plans",
    "None of the above",
]

Q10_OPTIONS = [
    "Daily work plans",
    "Safety alerts and emergency messages",
    "Weather-related updates affecting work",
    "Work or operational updates",
    "Equipment or fleet updates",
    "Training or skill-building opportunities",
    "HR updates (pay, leave, benefits, policies)",
    "License or certification reminders",
    "SHA or community events",
    "Employee wellness programs or available resources",
    "Career development opportunities",
]

Q11_OPTIONS = [
    "Face-to-face communication with supervisor",
    "Morning meetings",
    "Town Hall meetings",
    "Phone call",
    "Text/SMS",
    "Bulletin board / flyers",
    "Email",
    "Visix overhead screens",
]

Q12_SCALE = ["Not at all", "A little", "Somewhat", "Very much", "Extremely"]
Q12_ITEMS = [
    ("q12_supervisor", "Supervisor"),
    ("q12_morning_meetings", "Morning meetings"),
    ("q12_town_hall", "Town Hall meetings"),
    ("q12_phone_call", "Phone call"),
    ("q12_text_sms", "Text/SMS"),
    ("q12_bulletin_board", "Bulletin board"),
    ("q12_email", "Email"),
    ("q12_visix", "Visix screens"),
]

Q13_OPTIONS = [
    "Less than once a month",
    "1-2 times per month",
    "1-2 times per week",
    "3-5 times per week",
    "Daily",
]

Q14_OPTIONS = ["Not at all", "Slightly", "Somewhat", "Mostly", "Very much"]
Q15_OPTIONS = ["Not at all", "Slightly", "Somewhat", "Mostly", "Very much"]

Q16_OPTIONS = [
    "Very difficult",
    "Difficult",
    "Neither easy nor difficult",
    "Easy",
    "Very easy",
]

Q17_OPTIONS = ["Never", "Rarely", "Sometimes", "Often", "Always", "Not applicable"]

Q18_SCALE = ["Not at all", "A little", "Somewhat", "Very much", "Extremely"]
Q18_ITEMS = [
    ("q18_supervisor_person", "Talking directly to my supervisor (in person)"),
    ("q18_anonymous", "Anonymous box or anonymous form"),
    ("q18_direct_email", "Direct emails to supervisors or managers"),
    ("q18_official_channel", "Using an official SHA feedback channel (feedback email, online form, hotline)"),
    ("q18_morning_meetings", "Sharing during morning meetings"),
    ("q18_town_hall", "Sharing during Town Hall"),
    ("q18_point_of_contact", "Having a clear point-of-contact person for feedback"),
]

Q19_OPTIONS = ["Not at all", "Slightly", "Somewhat", "Mostly", "Very much"]

Q20_SCALE = ["Not useful at all", "Slightly useful", "Moderately useful", "Useful", "Very useful"]
Q20_ITEMS = [
    ("q20_bulletin_boards", "Having bulletin boards that are clearly organized and updated regularly"),
    ("q20_visix_updates", "More timely and accurate updates on Visix screens"),
    ("q20_sms_alerts", "Short text/SMS alerts for urgent or time-sensitive information"),
    ("q20_state_phone", "Providing a state-issued phone or device to improve access to work communication"),
    ("q20_town_hall", "More consistent town hall meetings for information sharing and feedback"),
    ("q20_clear_responsibility", "Clear responsibility for who updates and maintains communication channels (boards, Visix, messages)"),
    ("q20_reduce_repeated", "Reducing repeated or inconsistent messages from different sources"),
    ("q20_weekly_digest", "Weekly digest for non-urgent updates"),
    ("q20_training_tools", "Training to help staff better use communication tools and systems"),
    ("q20_replace_computers", "Replacing aging or outdated computers in the shop"),
    ("q20_kiosks", "Electronic kiosks in offices and shops"),
    ("q20_sha_mobile_phone", "Being issued an SHA mobile phone"),
]

# ---------------------------------------------------------------------------
# Build the OpenAI JSON-schema (for response_format)
# ---------------------------------------------------------------------------

def _nullable_enum(options: list[str]) -> dict:
    return {"type": ["string", "null"], "enum": [*options, None]}


def _nullable_int_1_5() -> dict:
    return {"type": ["integer", "null"], "enum": [1, 2, 3, 4, 5, None]}


def _nullable_string() -> dict:
    return {"type": ["string", "null"]}


def _string_array(options: list[str]) -> dict:
    return {
        "type": "array",
        "items": {"type": "string", "enum": options},
    }


def build_json_schema() -> dict:
    """Return the full JSON schema dict for OpenAI structured output."""
    props: dict = {}
    required: list[str] = []

    def add(name: str, schema: dict):
        props[name] = schema
        required.append(name)

    add("q1_role", _nullable_string())
    add("q2_district", _nullable_string())
    add("q3_shop", _nullable_string())
    add("q4_years_at_sha", _nullable_enum(Q4_OPTIONS))

    for col, _ in Q5_ITEMS:
        add(col, _nullable_int_1_5())
    for col, _ in Q6_ITEMS:
        add(col, _nullable_int_1_5())

    add("q7_timely_info", _nullable_enum(Q7_OPTIONS))
    add("q8_miss_info", _nullable_enum(Q8_OPTIONS))

    add("q9_selections", _string_array(Q9_OPTIONS))
    add("q9_other", _nullable_string())
    add("q10_selections", _string_array(Q10_OPTIONS))
    add("q10_other", _nullable_string())
    add("q11_selections", _string_array(Q11_OPTIONS))
    add("q11_other", _nullable_string())

    for col, _ in Q12_ITEMS:
        add(col, _nullable_int_1_5())

    add("q13_email_freq", _nullable_enum(Q13_OPTIONS))
    add("q14_awareness", _nullable_enum(Q14_OPTIONS))
    add("q15_comfort", _nullable_enum(Q15_OPTIONS))
    add("q16_feedback_ease", _nullable_enum(Q16_OPTIONS))
    add("q17_feedback_action", _nullable_enum(Q17_OPTIONS))

    for col, _ in Q18_ITEMS:
        add(col, _nullable_int_1_5())
    add("q18_other_text", _nullable_string())
    add("q18_other_rating", _nullable_int_1_5())

    add("q19_feel_important", _nullable_enum(Q19_OPTIONS))

    for col, _ in Q20_ITEMS:
        add(col, _nullable_int_1_5())

    add("q21_comments", _nullable_string())
    add("_confidence_notes", {"type": "string"})

    return {
        "name": "survey_response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": props,
            "required": required,
            "additionalProperties": False,
        },
    }


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert data-entry assistant. You will be given scanned images of a \
hand-filled paper survey titled "SHA Internal Communication Survey — Field Employee". \
The survey has 21 questions across 6 pages.

Your task: extract every answer from the scanned pages and return a single JSON \
object that conforms exactly to the schema provided.

RULES:
1. For Likert / rating-scale questions (Q5, Q6, Q12, Q18, Q20), return an integer \
1–5 where 1 = leftmost option and 5 = rightmost option. If no bubble is filled, \
return null.
2. For single-choice questions (Q4, Q7, Q8, Q13–Q17, Q19), return the exact option \
text string that is filled in. If nothing is filled, return null.
3. For multi-select / checkbox questions (Q9, Q10, Q11), return an array of the \
selected option strings. If nothing is checked, return an empty array [].
4. For free-text fields (Q1, Q2, Q3, Q21, and any "Other" write-in), transcribe \
the handwritten text as accurately as possible. Return null if blank.
5. If a mark is ambiguous (partially filled bubble, stray mark, etc.), use your \
best judgment and note it in _confidence_notes.
6. The _confidence_notes field MUST always be present. List any answers you are \
uncertain about, e.g. "Q3: handwriting unclear, read as 'Gaithersburg'". \
If everything is clear, write "All answers clear.".
"""

USER_PROMPT_TEMPLATE = """\
Below are the {n_pages} scanned page images of one completed questionnaire. \
Please extract all answers and return the JSON object.

QUESTION REFERENCE:
Q1. Current role/job in MDOT SHA (free text)
Q2. District (free text)
Q3. Shop (free text)
Q4. Years worked for SHA: {q4_opts}
Q5. Satisfaction with internal communication (1=Very dissatisfied … 5=Very satisfied):
{q5_items}
Q6. Agreement about direct supervisor (1=Very disagree … 5=Very agree):
{q6_items}
Q7. How often receive info early enough: {q7_opts}
Q8. How often miss relevant info: {q8_opts}
Q9. Types of info received timely (check all): {q9_opts}  + Other (write-in)
Q10. Types most interested in (check all): {q10_opts}  + Other (write-in)
Q11. Usual info sources (check all): {q11_opts}  + Other (write-in)
Q12. Preferred channels (1=Not at all … 5=Extremely):
{q12_items}
Q13. How often check SHA email: {q13_opts}
Q14. Awareness of whom to go to: {q14_opts}
Q15. Comfort speaking up: {q15_opts}
Q16. Ease of giving feedback: {q16_opts}
Q17. Feedback leads to action: {q17_opts}
Q18. Preferred feedback methods (1=Not at all … 5=Extremely):
{q18_items}
  + Other (write-in text and rating)
Q19. Communication makes you feel important: {q19_opts}
Q20. Usefulness of improvements (1=Not useful at all … 5=Very useful):
{q20_items}
Q21. Other comments/suggestions (free text)
"""


def build_user_prompt(n_pages: int) -> str:
    def _fmt_items(items):
        return "\n".join(f"  - {label}" for _, label in items)

    def _fmt_opts(opts):
        return " | ".join(opts)

    return USER_PROMPT_TEMPLATE.format(
        n_pages=n_pages,
        q4_opts=_fmt_opts(Q4_OPTIONS),
        q5_items=_fmt_items(Q5_ITEMS),
        q6_items=_fmt_items(Q6_ITEMS),
        q7_opts=_fmt_opts(Q7_OPTIONS),
        q8_opts=_fmt_opts(Q8_OPTIONS),
        q9_opts=_fmt_opts(Q9_OPTIONS),
        q10_opts=_fmt_opts(Q10_OPTIONS),
        q11_opts=_fmt_opts(Q11_OPTIONS),
        q12_items=_fmt_items(Q12_ITEMS),
        q13_opts=_fmt_opts(Q13_OPTIONS),
        q14_opts=_fmt_opts(Q14_OPTIONS),
        q15_opts=_fmt_opts(Q15_OPTIONS),
        q16_opts=_fmt_opts(Q16_OPTIONS),
        q17_opts=_fmt_opts(Q17_OPTIONS),
        q18_items=_fmt_items(Q18_ITEMS),
        q19_opts=_fmt_opts(Q19_OPTIONS),
        q20_items=_fmt_items(Q20_ITEMS),
    )


# ---------------------------------------------------------------------------
# Column ordering for CSV / Excel export
# ---------------------------------------------------------------------------

def get_all_columns() -> list[str]:
    """Return the ordered list of all output column names."""
    cols = ["source_file", "q1_role", "q2_district", "q3_shop", "q4_years_at_sha"]
    cols += [c for c, _ in Q5_ITEMS]
    cols += [c for c, _ in Q6_ITEMS]
    cols += ["q7_timely_info", "q8_miss_info"]
    cols += ["q9_selections", "q9_other"]
    cols += ["q10_selections", "q10_other"]
    cols += ["q11_selections", "q11_other"]
    cols += [c for c, _ in Q12_ITEMS]
    cols += ["q13_email_freq", "q14_awareness", "q15_comfort",
             "q16_feedback_ease", "q17_feedback_action"]
    cols += [c for c, _ in Q18_ITEMS]
    cols += ["q18_other_text", "q18_other_rating"]
    cols += ["q19_feel_important"]
    cols += [c for c, _ in Q20_ITEMS]
    cols += ["q21_comments", "_confidence_notes"]
    return cols


# Expanded columns that split multi-select arrays into individual binary flags
MULTI_SELECT_EXPANSIONS = {
    "q9_selections": Q9_OPTIONS,
    "q10_selections": Q10_OPTIONS,
    "q11_selections": Q11_OPTIONS,
}
